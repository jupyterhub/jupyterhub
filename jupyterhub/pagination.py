"""Basic class to manage pagination utils."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

class Pagination():

    _page_name = 'page'
    _per_page_name = 'per_page'
    _default_page = 1
    _default_per_page = 100
    _max_per_page = 250
    _record_name = 'users'
    _display_msg = (
        'Displaying {record_name} <b>{start} - {end}</b>. Total {record_name}: {total}'
    )

    def __init__(self, *args, **kwargs):
        """Potential parameters.
        **url**: URL in request
        **page**: current page in use
        **per_page**: number of records to display in the page. By default 100
        **total**: total records considered while paginating
        **display_msg**: informative text for pagination
        **record_name**: name of the record, showed in pagination info
        """
        self.page = kwargs.get(self._page_name, 1)

        if self.per_page > self._max_per_page:
            self.per_page = self._max_per_page

        self.total = int(kwargs.get('total', 0))
        self.display_msg = kwargs.get('display_msg', self._display_msg)

        self.record_name = kwargs.get('record_name', self._record_name)
        self.url = kwargs.get('url') or self.get_url()
        self.init_values()

    def init_values(self):
        self._cached = {}
        self.skip = (self.page - 1) * self.per_page
        pages = divmod(self.total, self.per_page)
        self.total_pages = pages[0] + 1 if pages[1] else pages[0]

        self.has_prev = self.page > 1
        self.has_next = self.page < self.total_pages

    @classmethod
    def get_page_args(self, handler):
        self.page = handler.get_argument(self._page_name, self._default_page)
        self.per_page = handler.get_argument(
            self._per_page_name, self._default_per_page
        )
        try:
            self.per_page = int(self.per_page)
            if self.per_page > self._max_per_page:
                self.per_page = self._max_per_page
        except:
            self.per_page = self._default_per_page

        try:
            self.page = int(self.page)
        except:
            self.page = self._default_page

        return self.page, self.per_page, self.per_page * (self.page - 1)
