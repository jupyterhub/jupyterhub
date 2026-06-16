"""SAIEP native admin interface — resources (Docker/Swarm) + internal monitoring.

Replaces the external Portainer tool with a JupyterHub-integrated, admin-only
interface (no third-party branding). Exposes:
  GET  /hub/swarm                 -> the single-page admin UI
  GET  /hub/swarm/api/<section>   -> JSON data (overview/containers/volumes/
                                     networks/nodes/metrics)
  POST /hub/swarm/action          -> perform an action (start/stop/remove/
                                     create/update/swarm init...)
All endpoints require an authenticated JupyterHub admin.
"""
import asyncio
import json
import math
import os
import time
from urllib.parse import quote

import docker as docker_sdk
from tornado import web
from tornado.httpclient import AsyncHTTPClient

from jupyterhub.handlers import BaseHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_IP = '104.248.22.193'
PROM_URL = 'http://127.0.0.1:9090'

GiB = 1073741824


def _client():
    return docker_sdk.from_env()


async def _run(fn, *args, **kwargs):
    """Run a blocking docker SDK call off the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


class _AdminBase(BaseHandler):
    def _require_admin(self):
        user = self.current_user
        if not user or not user.admin:
            raise web.HTTPError(403, "Accès réservé aux administrateurs")
        return user


class ResourcesIndexHandler(_AdminBase):
    @web.authenticated
    async def get(self):
        self._require_admin()
        path = os.path.join(BASE_DIR, 'static', 'admin', 'index.html')
        with open(path, 'r', encoding='utf-8') as f:
            self.finish(f.read())


class ResourcesApiHandler(_AdminBase):
    @web.authenticated
    async def get(self, section):
        self._require_admin()
        self.set_header('Content-Type', 'application/json')
        handler = getattr(self, '_section_' + section, None)
        if handler is None:
            raise web.HTTPError(404)
        try:
            data = await handler()
        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({'error': str(e)}))
            return
        self.finish(json.dumps(data))

    async def _section_overview(self):
        c = _client()
        info = await _run(c.info)
        swarm = info.get('Swarm', {})
        return {
            'ncpu': info.get('NCPU', 0),
            'mem_gb': round(info.get('MemTotal', 0) / GiB, 1),
            'containers': info.get('Containers', 0),
            'running': info.get('ContainersRunning', 0),
            'images': info.get('Images', 0),
            'docker_version': info.get('ServerVersion', ''),
            'swarm_active': swarm.get('LocalNodeState') == 'active',
            'nodes': swarm.get('Nodes', 1) if swarm.get('LocalNodeState') == 'active' else 1,
            'hostname': info.get('Name', ''),
        }

    async def _section_containers(self):
        c = _client()
        items = await _run(c.containers.list, all=True)
        out = []
        for x in items:
            image = x.image.tags[0] if x.image.tags else x.image.short_id
            ports = []
            try:
                for cont, binds in (x.attrs['NetworkSettings']['Ports'] or {}).items():
                    if binds:
                        for b in binds:
                            ports.append('%s->%s' % (b.get('HostPort', ''), cont))
            except Exception:
                pass
            out.append({
                'id': x.short_id,
                'name': x.name,
                'image': image,
                'status': x.status,
                'state': x.attrs.get('State', {}).get('Status', x.status),
                'ports': ', '.join(ports),
            })
        return {'containers': out}

    async def _section_volumes(self):
        c = _client()
        vols = await _run(c.volumes.list)
        return {'volumes': [
            {'name': v.name, 'driver': v.attrs.get('Driver', ''),
             'mountpoint': v.attrs.get('Mountpoint', '')}
            for v in vols
        ]}

    async def _section_networks(self):
        c = _client()
        nets = await _run(c.networks.list)
        return {'networks': [
            {'id': n.short_id, 'name': n.name,
             'driver': n.attrs.get('Driver', ''),
             'scope': n.attrs.get('Scope', '')}
            for n in nets
        ]}

    async def _section_images(self):
        c = _client()
        imgs = await _run(c.images.list)
        out = []
        for i in imgs:
            out.append({
                'id': i.short_id.replace('sha256:', ''),
                'tags': i.tags or ['<none>'],
                'size_mb': round(i.attrs.get('Size', 0) / 1048576, 1),
            })
        return {'images': out}

    async def _section_nodes(self):
        c = _client()
        info = await _run(c.info)
        active = info.get('Swarm', {}).get('LocalNodeState') == 'active'
        result = {'swarm_active': active, 'nodes': [], 'join_command': None,
                  'total_cpu': info.get('NCPU', 0),
                  'total_mem_gb': round(info.get('MemTotal', 0) / GiB, 1)}
        if not active:
            return result
        nodes = await _run(c.nodes.list)
        total_cpu, total_mem, manager_addr = 0, 0, None
        for n in nodes:
            a = n.attrs
            res = a.get('Description', {}).get('Resources', {})
            ncpu = round(res.get('NanoCPUs', 0) / 1e9)
            total_cpu += ncpu
            total_mem += res.get('MemoryBytes', 0)
            role = a.get('Spec', {}).get('Role', '')
            if role == 'manager' and a.get('ManagerStatus', {}).get('Addr'):
                manager_addr = a['ManagerStatus']['Addr']
            result['nodes'].append({
                'id': n.id,
                'hostname': a.get('Description', {}).get('Hostname', ''),
                'role': role,
                'state': a.get('Status', {}).get('State', ''),
                'availability': a.get('Spec', {}).get('Availability', ''),
                'leader': a.get('ManagerStatus', {}).get('Leader', False),
                'cpu': ncpu,
                'mem_gb': round(res.get('MemoryBytes', 0) / GiB, 1),
            })
        result['total_cpu'] = total_cpu
        result['total_mem_gb'] = round(total_mem / GiB, 1)
        token = c.swarm.attrs.get('JoinTokens', {}).get('Worker')
        if token and manager_addr:
            result['join_command'] = 'docker swarm join --token %s %s' % (token, manager_addr)
        return result


async def _prom(query, rng=False, hours=3):
    http = AsyncHTTPClient()
    if rng:
        end = int(time.time())
        start = end - hours * 3600
        step = max(60, int(hours * 3600 / 90))
        url = '%s/api/v1/query_range?query=%s&start=%d&end=%d&step=%d' % (
            PROM_URL, quote(query), start, end, step)
    else:
        url = '%s/api/v1/query?query=%s' % (PROM_URL, quote(query))
    try:
        resp = await http.fetch(url, request_timeout=8)
        return json.loads(resp.body)
    except Exception:
        return {'data': {'result': []}}


def _instant(j, default=0):
    r = j.get('data', {}).get('result', [])
    if r:
        try:
            v = float(r[0]['value'][1])
            return v if math.isfinite(v) else default
        except Exception:
            return default
    return default


def _series(j, rounding=2):
    """First series of a range query -> list of {t (ms), y} points.
    Prometheus returns "NaN"/"+Inf" (e.g. histogram_quantile with no samples);
    those are not valid JSON, so we skip non-finite points."""
    for res in j.get('data', {}).get('result', []):
        out = []
        for v in res.get('values', []):
            try:
                y = float(v[1])
            except Exception:
                continue
            if not math.isfinite(y):
                continue
            out.append({'t': int(v[0]) * 1000, 'y': round(y, rounding)})
        return out
    return []


async def gather_metrics(hours=3):
    servers = _instant(await _prom('jupyterhub_running_servers'))
    users_24h = _instant(await _prom('jupyterhub_active_users{period="24h"}'))
    users_7d = _instant(await _prom('jupyterhub_active_users{period="7d"}'))
    users_30d = _instant(await _prom('jupyterhub_active_users{period="30d"}'))
    total_users = _instant(await _prom('jupyterhub_total_users'))

    return {
        'servers': servers,
        'users_24h': users_24h,
        'users_7d': users_7d,
        'users_30d': users_30d,
        'total_users': total_users,
        'hours': hours,
        'servers_series': _series(
            await _prom('jupyterhub_running_servers', rng=True, hours=hours), 0),
        'request_rate': _series(
            await _prom('sum(rate(jupyterhub_request_duration_seconds_count[5m]))',
                        rng=True, hours=hours), 3),
        'latency_p95': _series(
            await _prom('histogram_quantile(0.95, sum(rate('
                        'jupyterhub_request_duration_seconds_bucket[5m])) by (le))',
                        rng=True, hours=hours), 3),
        'spawn_p95': _series(
            await _prom('histogram_quantile(0.95, sum(rate('
                        'jupyterhub_server_spawn_duration_seconds_bucket[10m])) by (le))',
                        rng=True, hours=hours), 2),
    }


class ResourcesActionHandler(_AdminBase):
    @web.authenticated
    async def post(self):
        self._require_admin()
        self.set_header('Content-Type', 'application/json')
        try:
            body = json.loads(self.request.body or '{}')
        except Exception:
            body = {}
        action = body.get('action', '')
        target = body.get('target', '')
        params = body.get('params', {}) or {}
        c = _client()
        try:
            result = await self._do(c, action, target, params)
            self.finish(json.dumps({'ok': True, 'result': result}))
        except Exception as e:
            self.set_status(400)
            self.finish(json.dumps({'ok': False, 'error': str(e)}))

    async def _do(self, c, action, target, params):
        # --- containers ---
        if action == 'container.start':
            await _run((await _run(c.containers.get, target)).start); return 'démarré'
        if action == 'container.stop':
            await _run((await _run(c.containers.get, target)).stop); return 'arrêté'
        if action == 'container.restart':
            await _run((await _run(c.containers.get, target)).restart); return 'redémarré'
        if action == 'container.remove':
            await _run((await _run(c.containers.get, target)).remove, force=True); return 'supprimé'
        if action == 'container.logs':
            x = await _run(c.containers.get, target)
            logs = await _run(x.logs, tail=300)
            return logs.decode('utf-8', 'replace')
        if action == 'container.inspect':
            x = await _run(c.containers.get, target)
            a = x.attrs
            cfg = a.get('Config', {})
            hostcfg = a.get('HostConfig', {})
            ports = []
            for cont, binds in (a.get('NetworkSettings', {}).get('Ports') or {}).items():
                if binds:
                    ports += ['%s→%s' % (b.get('HostPort', ''), cont) for b in binds]
                else:
                    ports.append(cont)
            mounts = ['%s → %s' % (m.get('Source', m.get('Name', '')), m.get('Destination', ''))
                      for m in a.get('Mounts', [])]
            nets = list((a.get('NetworkSettings', {}).get('Networks') or {}).keys())
            return {
                'name': a.get('Name', '').lstrip('/'),
                'image': cfg.get('Image', ''),
                'state': a.get('State', {}).get('Status', ''),
                'created': (a.get('Created', '') or '')[:19].replace('T', ' '),
                'command': ' '.join(cfg.get('Cmd') or []) or (cfg.get('Entrypoint') and ' '.join(cfg['Entrypoint'])) or '',
                'restart_policy': (hostcfg.get('RestartPolicy') or {}).get('Name', ''),
                'mem_limit_mb': round((hostcfg.get('Memory') or 0) / 1048576, 1),
                'nano_cpus': round((hostcfg.get('NanoCpus') or 0) / 1e9, 2),
                'ports': ports,
                'mounts': mounts,
                'networks': nets,
                'env': cfg.get('Env') or [],
                'labels': cfg.get('Labels') or {},
            }
        if action == 'container.stats':
            x = await _run(c.containers.get, target)
            s = await _run(x.stats, stream=False)
            cpu = s.get('cpu_stats', {}); pre = s.get('precpu_stats', {})
            cd = cpu.get('cpu_usage', {}).get('total_usage', 0) - pre.get('cpu_usage', {}).get('total_usage', 0)
            sd = cpu.get('system_cpu_usage', 0) - pre.get('system_cpu_usage', 0)
            ncpu = cpu.get('online_cpus') or len(cpu.get('cpu_usage', {}).get('percpu_usage') or [1])
            cpu_pct = round((cd / sd) * ncpu * 100, 1) if sd > 0 else 0.0
            mem = s.get('memory_stats', {})
            usage = mem.get('usage', 0); limit = mem.get('limit', 0)
            rx = tx = 0
            for n in (s.get('networks') or {}).values():
                rx += n.get('rx_bytes', 0); tx += n.get('tx_bytes', 0)
            return {
                'cpu_pct': cpu_pct,
                'mem_mb': round(usage / 1048576, 1),
                'mem_limit_mb': round(limit / 1048576, 1),
                'mem_pct': round(usage / limit * 100, 1) if limit else 0,
                'net_rx_mb': round(rx / 1048576, 2),
                'net_tx_mb': round(tx / 1048576, 2),
            }
        if action == 'container.update':
            x = await _run(c.containers.get, target)
            kw = {}
            if params.get('mem_gb'):
                kw['mem_limit'] = int(float(params['mem_gb']) * GiB)
            if params.get('cpus'):
                kw['nano_cpus'] = int(float(params['cpus']) * 1e9)
            await _run(x.update, **kw); return 'limites mises à jour'
        if action == 'container.create':
            await _run(c.containers.run, params['image'], name=params.get('name') or None,
                       command=params.get('command') or None, detach=True,
                       restart_policy={'Name': 'unless-stopped'})
            return 'conteneur créé'
        # --- images ---
        if action == 'image.pull':
            await _run(c.images.pull, params['name']); return 'image téléchargée'
        if action == 'image.remove':
            await _run(c.images.remove, target, force=True); return 'image supprimée'
        # --- volumes ---
        if action == 'volume.create':
            await _run(c.volumes.create, name=params['name']); return 'volume créé'
        if action == 'volume.remove':
            await _run((await _run(c.volumes.get, target)).remove, force=True); return 'volume supprimé'
        # --- networks ---
        if action == 'network.create':
            await _run(c.networks.create, params['name'],
                       driver=params.get('driver') or 'bridge'); return 'réseau créé'
        if action == 'network.remove':
            await _run((await _run(c.networks.get, target)).remove); return 'réseau supprimé'
        # --- swarm / nodes ---
        if action == 'swarm.init':
            await _run(c.swarm.init, advertise_addr=PUBLIC_IP); return 'cluster activé'
        if action == 'swarm.leave':
            await _run(c.swarm.leave, force=True); return 'cluster désactivé'
        if action == 'node.drain':
            n = await _run(c.nodes.get, target)
            spec = dict(n.attrs['Spec']); spec['Availability'] = 'drain'
            await _run(n.update, spec); return 'nœud drainé'
        if action == 'node.activate':
            n = await _run(c.nodes.get, target)
            spec = dict(n.attrs['Spec']); spec['Availability'] = 'active'
            await _run(n.update, spec); return 'nœud activé'
        if action == 'node.remove':
            await _run((await _run(c.nodes.get, target)).remove, force=True); return 'nœud retiré'
        raise web.HTTPError(400, 'Action inconnue: %s' % action)


class MonitoringIndexHandler(_AdminBase):
    @web.authenticated
    async def get(self):
        self._require_admin()
        path = os.path.join(BASE_DIR, 'static', 'admin', 'monitoring.html')
        with open(path, 'r', encoding='utf-8') as f:
            self.finish(f.read())


class MonitoringApiHandler(_AdminBase):
    @web.authenticated
    async def get(self):
        self._require_admin()
        self.set_header('Content-Type', 'application/json')
        try:
            hours = max(1, min(360, int(self.get_query_argument('hours', '3'))))
        except Exception:
            hours = 3
        try:
            data = await gather_metrics(hours=hours)
        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({'error': str(e)}))
            return
        self.finish(json.dumps(data))


def resource_handlers():
    return [
        (r'/swarm', ResourcesIndexHandler),
        (r'/swarm/api/(\w+)', ResourcesApiHandler),
        (r'/swarm/action', ResourcesActionHandler),
        (r'/monitoring', MonitoringIndexHandler),
        (r'/monitoring/api/metrics', MonitoringApiHandler),
    ]
