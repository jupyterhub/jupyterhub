from pytablewriter import MarkdownTableWriter
from pytablewriter.style import Style

import jupyterhub.metrics

class Generator:

    def prometheus_metrics(self):
        filename = "./source/monitoring/metrics.md"

        writer = MarkdownTableWriter()
        writer.table_name = "List of Prometheus Metrics\n"
        writer.headers = ["Type", "Name", "Description"]
        writer.value_matrix = []
        writer.margin = 1

        for name in dir(jupyterhub.metrics):
            obj = getattr(jupyterhub.metrics, name)
            if obj.__class__.__module__.startswith('prometheus_client.'):
                for metric in obj.describe():
                    writer.value_matrix.append([metric.type, metric.name, metric.documentation])

        with open(filename, 'w') as f:
            f.write(writer.dumps())

def main():
    doc_generator = Generator()
    doc_generator.prometheus_metrics()


if __name__ == "__main__":
    main()
