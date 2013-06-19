import os
from component import Component

class Djvused(Component):

    """
    Multi Purpose DjVu Document Editor

    """

    args = ['options', 'script', 'djvu_file']
    executable = 'djvused'

    def __init__(self, book):
        super(Djvused, self).__init__(Djvused.args)
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + self.book.identifier + '_derived'}
        self.book.add_dirs(dirs)
        

    def run(self):
        if not os.path.exists(self.djvu_file):
            raise IOError('Cannot find ' + self.djvu_file)
        try:
            self.execute()
        except Exception as e:
            raise e
