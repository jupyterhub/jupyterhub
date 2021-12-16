"""
Simple empty class that returns itself for all functions called on it.
This allows us to call any method of any name on this, and it'll return another
instance of itself that'll allow any method to be called on it.

Primarily used to mock out the statsd client when statsd is not being used
"""


class EmptyClass:
    def empty_function(self, *args, **kwargs):
        return self

    def __getattr__(self, attr):
        return self.empty_function
