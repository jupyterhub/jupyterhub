"""Basic class to manage pagination utils."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from traitlets import Bool
from traitlets import default
from traitlets import Integer
from traitlets import observe
from traitlets import Unicode
from traitlets import validate
from traitlets.config import Configurable


class Pagination(Configurable):

    # configurable options
    default_per_page = Integer(
        100,
        config=True,
        help="Default number of entries per page for paginated results.",
    )

    max_per_page = Integer(
        250,
        config=True,
        help="Maximum number of entries per page for paginated results.",
    )

    # state variables
    url = Unicode("")
    page = Integer(1)
    per_page = Integer(1, min=1)

    @default("per_page")
    def _default_per_page(self):
        return self.default_per_page

    @validate("per_page")
    def _limit_per_page(self, proposal):
        if self.max_per_page and proposal.value > self.max_per_page:
            return self.max_per_page
        if proposal.value <= 1:
            return 1
        return proposal.value

    @observe("max_per_page")
    def _apply_max(self, change):
        if change.new:
            self.per_page = min(change.new, self.per_page)

    total = Integer(0)

    total_pages = Integer(0)

    @default("total_pages")
    def _calculate_total_pages(self):
        total_pages = self.total // self.per_page
        if self.total % self.per_page:
            # there's a remainder, add 1
            total_pages += 1
        return total_pages

    @observe("per_page", "total")
    def _update_total_pages(self, change):
        """Update total_pages when per_page or total is changed"""
        self.total_pages = self._calculate_total_pages()

    separator = Unicode("...")

    def get_page_args(self, handler):
        """
        This method gets the arguments used in the webpage to configurate the pagination
        In case of no arguments, it uses the default values from this class

        Returns:
          - page: The page requested for paginating or the default value (1)
          - per_page: The number of items to return in this page. No more than max_per_page
          - offset: The offset to consider when managing pagination via the ORM
        """
        page = handler.get_argument("page", 1)
        per_page = handler.get_argument("per_page", self.default_per_page)
        try:
            self.per_page = int(per_page)
        except Exception:
            self.per_page = self._default_per_page

        try:
            self.page = int(page)
            if self.page < 1:
                self.page = 1
        except:
            self.page = 1

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

        before_page = 2
        after_page = 2
        window_size = before_page + after_page + 1

        # Add 1 to total_pages since our starting page is 1 and not 0
        last_page = self.total_pages

        pages = []

        # will default window + start, end fit without truncation?
        if self.total_pages > window_size + 2:
            if self.page - before_page > 1:
                # before_page will not reach page 1
                pages.append(1)
                if self.page - before_page > 2:
                    # before_page will not reach page 2, need separator
                    pages.append(self.separator)

            pages.extend(range(max(1, self.page - before_page), self.page))
            # we now have up to but not including self.page

            if self.page + after_page + 1 >= last_page:
                # after_page gets us to the end
                pages.extend(range(self.page, last_page + 1))
            else:
                # add full after_page entries
                pages.extend(range(self.page, self.page + after_page + 1))
                # add separator *if* this doesn't get to last page - 1
                if self.page + after_page < last_page - 1:
                    pages.append(self.separator)
                pages.append(last_page)

            return pages

        else:
            # everything will fit, nothing to think about
            # always return at least one page
            return list(range(1, last_page + 1)) or [1]

    @property
    def links(self):
        """Get the links for the pagination.
           Getting the input from calculate_pages_window(), generates the HTML code
           for the pages to render, plus the arrows to go onwards and backwards (if needed).
           """
        if self.total_pages == 1:
            return []

        pages_to_render = self.calculate_pages_window()

        links = ['<nav>']
        links.append('<ul class="pagination">')

        if self.page > 1:
            prev_page = self.page - 1
            links.append(
                '<li><a href="?page={prev_page}">«</a></li>'.format(prev_page=prev_page)
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
            elif page == self.separator:
                links.append(
                    '<li class="disabled"><span> <span aria-hidden="true">{separator}</span></span></li>'.format(
                        separator=self.separator
                    )
                )
            else:
                links.append(
                    '<li><a href="?page={page}">{page}</a></li>'.format(page=page)
                )

        if self.page >= 1 and self.page < self.total_pages:
            next_page = self.page + 1
            links.append(
                '<li><a href="?page={next_page}">»</a></li>'.format(next_page=next_page)
            )
        else:
            links.append(
                '<li class="disabled"><span><span aria-hidden="true">»</span></span></li>'
            )

        links.append('</ul>')
        links.append('</nav>')

        return ''.join(links)
