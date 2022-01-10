"""
This script updates two files with the RBAC scope descriptions found in
`scopes.py`.

The files are:

    1. scope-table.md

       This file is git ignored and referenced by the documentation.

    2. rest-api.yml

       This file is JupyterHub's REST API schema. Both a version and the RBAC
       scopes descriptions are updated in it.
"""
import os
from collections import defaultdict
from pathlib import Path
from subprocess import run

from pytablewriter import MarkdownTableWriter
from ruamel.yaml import YAML

from jupyterhub import __version__
from jupyterhub.scopes import scope_definitions

HERE = os.path.abspath(os.path.dirname(__file__))
DOCS = Path(HERE).parent.parent.absolute()
REST_API_YAML = DOCS.joinpath("source", "_static", "rest-api.yml")
SCOPE_TABLE_MD = Path(HERE).joinpath("scope-table.md")


class ScopeTableGenerator:
    def __init__(self):
        self.scopes = scope_definitions

    @classmethod
    def create_writer(cls, table_name, headers, values):
        writer = MarkdownTableWriter()
        writer.table_name = table_name
        writer.headers = headers
        writer.value_matrix = values
        writer.margin = 1
        return writer

    def _get_scope_relationships(self):
        """Returns a tuple of dictionary of all scope-subscope pairs and a list of just subscopes:

        ({scope: subscope}, [subscopes])

        used for creating hierarchical scope table in _parse_scopes()
        """
        pairs = []
        for scope, data in self.scopes.items():
            subscopes = data.get('subscopes')
            if subscopes is not None:
                for subscope in subscopes:
                    pairs.append((scope, subscope))
            else:
                pairs.append((scope, None))
        subscopes = [pair[1] for pair in pairs]
        pairs_dict = defaultdict(list)
        for scope, subscope in pairs:
            pairs_dict[scope].append(subscope)
        return pairs_dict, subscopes

    def _get_top_scopes(self, subscopes):
        """Returns a list of highest level scopes
        (not a subscope of any other scopes)"""
        top_scopes = []
        for scope in self.scopes.keys():
            if scope not in subscopes:
                top_scopes.append(scope)
        return top_scopes

    def _parse_scopes(self):
        """Returns a list of table rows where row:
        [indented scopename string, scope description string]"""
        scope_pairs, subscopes = self._get_scope_relationships()
        top_scopes = self._get_top_scopes(subscopes)

        table_rows = []
        md_indent = "&nbsp;&nbsp;&nbsp;"

        def _add_subscopes(table_rows, scopename, depth=0):
            description = self.scopes[scopename]['description']
            doc_description = self.scopes[scopename].get('doc_description', '')
            if doc_description:
                description = doc_description
            table_row = [f"{md_indent * depth}`{scopename}`", description]
            table_rows.append(table_row)
            for subscope in scope_pairs[scopename]:
                if subscope:
                    _add_subscopes(table_rows, subscope, depth + 1)

        for scope in top_scopes:
            _add_subscopes(table_rows, scope)

        return table_rows

    def write_table(self):
        """Generates the RBAC scopes reference documentation as a markdown table
        and writes it to the .gitignored `scope-table.md`."""
        filename = SCOPE_TABLE_MD
        table_name = ""
        headers = ["Scope", "Grants permission to:"]
        values = self._parse_scopes()
        writer = self.create_writer(table_name, headers, values)

        title = "Table 1. Available scopes and their hierarchy"
        content = f"{title}\n{writer.dumps()}"
        with open(filename, 'w') as f:
            f.write(content)
        print(f"Generated {filename}.")
        print(
            "Run 'make clean' before 'make html' to ensure the built scopes.html contains latest scope table changes."
        )

    def write_api(self):
        """Loads `rest-api.yml` and writes it back with a dynamically set
        JupyterHub version field and list of RBAC scopes descriptions from
        `scopes.py`."""
        filename = REST_API_YAML

        yaml = YAML(typ="rt")
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, offset=2, sequence=4)

        scope_dict = {}
        with open(filename) as f:
            content = yaml.load(f.read())

        content["info"]["version"] = __version__
        for scope in self.scopes:
            description = self.scopes[scope]['description']
            doc_description = self.scopes[scope].get('doc_description', '')
            if doc_description:
                description = doc_description
            scope_dict[scope] = description
        content['components']['securitySchemes']['oauth2']['flows'][
            'authorizationCode'
        ]['scopes'] = scope_dict

        with open(filename, 'w') as f:
            yaml.dump(content, f)

        run(
            ['pre-commit', 'run', 'prettier', '--files', filename],
            cwd=HERE,
            check=False,
        )


def main():
    table_generator = ScopeTableGenerator()
    table_generator.write_table()
    table_generator.write_api()


if __name__ == "__main__":
    main()
