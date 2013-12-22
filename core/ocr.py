import os

from util import Util
from operation import Operation
from datastructures import Box


class OCR(Operation):

    components = {'tesseract': 'Tesseract'}

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        self.ocr_data = None
        try:
            super(OCR, self).__init__(OCR.components)
            self.init_components( [self.book] )
        except:
            self.ProcessHandler.join((self.book.identifier + '_OCR_init',
                                      Util.exception_info(),
                                      self.book.logger))


    def tesseract_hocr_pipeline(self, start, end, lang='eng'):
        for leaf in range(start, end):
            #if page is blank, we skip ocr on it
            #if not self.book.contentCrop.box[leaf].is_valid():
            #    self.complete_process(leaf, None)
            #    continue
            self.Tesseract.psm = '-psm 3'
            self.Tesseract.language = '-l ' + lang
            self.Tesseract.hocr = 'hocr'

            leafnum = '%04d' % leaf
            self.Tesseract.in_file = (self.book.dirs['cropped'] + '/' +
                                      self.book.identifier + '_' + str(leafnum) + '.JPG')
            self.Tesseract.out_base = (self.book.dirs['tesseract_ocr'] + '/' +
                                       self.book.identifier + '_' + str(leafnum))

            try:
                self.Tesseract.run(leaf)
            except:
                self.ProcessHandler.join((self.book.identifier +
                                          '_tesseract_hocr_pipeline',
                                          Util.exception_info(),
                                          self.book.logger))

