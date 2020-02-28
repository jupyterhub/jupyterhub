"""Basic class to manage pagination utils."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.


class Pagination:

    _page_name = 'page'
    _per_page_name = 'per_page'
    _default_page = 1
    _default_per_page = 100
    _max_per_page = 250

    def __init__(self, *args, **kwargs):
        """Potential parameters.
        **url**: URL in request
        **page**: current page in use
        **per_page**: number of records to display in the page. By default 100
        **total**: total records considered while paginating
        """
        self.page = kwargs.get(self._page_name, 1)

        if self.per_page > self._max_per_page:
            self.per_page = self._max_per_page

        self.total = int(kwargs.get('total', 0))
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
        """
        This method gets the arguments used in the webpage to configurate the pagination
        In case of no arguments, it uses the default values from this class

        It returns:
          - self.page: The page requested for paginating or the default value (1)
          - self.per_page: The number of items to return in this page. By default 100 and no more than 250
          - self.per_page * (self.page - 1): The offset to consider when managing pagination via the ORM
        """
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
            if self.page < 1:
                self.page = self._default_page
        except:
            self.page = self._default_page

        return self.page, self.per_page, self.per_page * (self.page - 1)

    @property
    def info(self):
        """Get the pagination information."""
        start = 1 + (self.page - 1) * self.per_page
        end = start + self.per_page - 1
        if end > self.total:
            end = self.total

        if start > self.total:
            start = self.total

        return {'total': self.total, 'start': start, 'end': end}

    def calculate_pages_window(self):
        """Calculates the set of pages to render later in links() method. 
           It returns the list of pages to render via links for the pagination 
           By default, as we've observed in other applications, we're going to render
           only a finite and predefined number of pages, avoiding visual fatigue related
           to a long list of pages. By default, we render 7 pages plus some inactive links with the characters '...'
           to point out that there are other pages that aren't explicitly rendered.
           The primary way of work is to provide current webpage and 5 next pages, the last 2 ones 
           (in case the current page + 5 does not overflow the total lenght of pages) and the first one for reference.
           """

        self.separator_character = '...'
        default_pages_to_render = 7
        after_page = 5
        before_end = 2

        pages = []

        if self.total_pages > default_pages_to_render:
            if self.page > 1:
                pages.extend([1, '...'])

            if self.total_pages < self.page + after_page:
                pages.extend(list(range(self.page, self.total_pages)))
            else:
                if self.total_pages > self.page + after_page + before_end:
                    pages.extend(list(range(self.page, self.page + after_page)))
                    pages.append('...')
                    pages.extend(
                        list(range(self.total_pages - before_end, self.total_pages))
                    )
                else:
                    pages.extend(list(range(self.page, self.page + after_page)))

            return pages

        else:
            return list(range(1, self.total_pages))

    @property
    def links(self):
        """Sets the links for the pagination.
           Getting the input from calculate_pages_window(), generates the HTML code 
           for the pages to render, plus the arrows to go onwards and backwards (if needed).
           """

        pages_to_render = self.calculate_pages_window()

        links = ['<nav>']
        links.append('<ul class="pagination">')

        if self.page > 1:
            prev_page = self.page - 1
            links.append(
                '<li><a href="/hub/admin?page={prev_page}">«</a></li>'.format(
                    prev_page=prev_page
                )
            )
        else:
            links.append(
                '<li class="disabled"><span><span aria-hidden="true">«</span></span></li>'
            )

        for page in list(pages_to_render):
            if page == self.page:
                links.append(
                    '<li class="active"><span>{page}<span class="sr-only">(current)</span></span></li>'.format(
                        page=page
                    )
                )
            elif page == self.separator_character:
                links.append(
                    '<li class="disabled"><span> <span aria-hidden="true">...</span></span></li>'
                )
            else:
                links.append(
                    f'<li><a href="/hub/admin?page={page}">{page}</a></li>'.format(
                        page=page
                    )
                )

        if self.page >= 1 and self.page < self.total_pages:
            next_page = self.page + 1
            links.append(
                f'<li><a href="/hub/admin?page={next_page}">»</a></li>'.format(
                    next_page=next_page
                )
            )
        else:
            links.append(
                '<li class="disabled"><span><span aria-hidden="true">»</span></span></li>'
            )

        links.append('</ul>')
        links.append('</nav>')

        return ''.join(links)
