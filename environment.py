import os
import sys
import platform
import glob
import re
import Image
import yaml
import datetime
import time
import shutil
from collections import OrderedDict
from lxml import etree

from util import Util
from datastructures import Crop

class Environment:

    settings = OrderedDict([('respawn', True),
                            ('autopaginate', False),
                            ('make_cornered_scaled', False),
                            ('draw_clusters', False),
                            ('draw_removed_clusters', False),
                            ('draw_invalid_clusters', False),
                            ('draw_content_dimensions', False),
                            ('draw_page_number_candidates', False),
                            ('draw_noise', False)])
    interface = 'command'
    proc_mode = None
    dir_mode = 0755
    scale_factor = 4


    def __init__(self, dir_list, args=None):
        Environment.set_current_path()
        Environment.check_system()
        self.books = []
        for root_dir in dir_list:
            if not self.find_valid_subdirs(root_dir):
                raw_data = Environment.is_sane(root_dir)
                if raw_data:
                    self.init_new_book(root_dir, raw_data)
        if len(self.books) < 1:
            Util.bail('No valid directories found for processing...')
        for book in self.books:
            book.start_time = time.time()
            book.settings = Environment.load_settings(book.root_dir, args)
            book.init_crops()
            book.logger = Logger()
            book.init_logs()
            Environment.log_settings(book)


    @staticmethod
    def log_settings(book):
        book.logger.message('*****SETTINGS*****')
        for setting, value in book.settings.items():
            book.logger.message(setting + ':' + str(value))
        book.logger.message('*****SETTINGS*****\n')


    @staticmethod
    def check_system():
        plat = sys.platform
        if re.search('linux', plat):
            Environment.platform = 'linux'
        if re.search('darwin', plat):
            Environment.platform = 'darwin'
        if re.search('win', plat):
            Environment.platform = 'win'
        Environment.architecture = platform.uname()[-2]


    @staticmethod
    def set_current_path():
        Environment.current_path = os.path.abspath(os.path.dirname(sys.argv[0]))
        sys.path.append(Environment.current_path)


    def find_valid_subdirs(self, root_dir):
        root_dir = root_dir.rstrip('/')
        subdirs = os.listdir(root_dir)
        for dir in subdirs:
            path = root_dir + '/' + dir
            raw_data = Environment.is_sane(path)
            if raw_data:
                self.init_new_book(path, raw_data)
        if len(self.books) > 1:
            return True
        else:
            return False


    def init_new_book(self, book_dir, raw_data):
        book = BookData(book_dir, raw_data)
        if book not in self.books:
            self.books.append(book)


    @staticmethod
    def find_raw_dir(dir):
        dir_items = os.listdir(dir)
        for item in dir_items:
            if re.search("(_raw_|_RAW_)", item):
                if os.path.isdir(dir + '/' + item):
                    return item


    @staticmethod
    def is_sane(dir):
        if not os.path.isdir(dir):
            return False
        raw_dir = Environment.find_raw_dir(dir)
        if raw_dir is None:
            return False
        else:
            raw_images, raw_dimensions = Environment.get_raw_images(dir + '/' + raw_dir)
        return {'page_count': len(raw_images),
                'images': raw_images,
                'dimensions': raw_dimensions}


    @staticmethod
    def get_raw_images(dir):
        raw_images = glob.glob(dir + '/*')
        raw_dimensions = {}
        for leaf, file in enumerate(raw_images):
            if re.search("[\.(jpg|JPG|jpeg|JPEG)]$",file) is None:
                Util.bail("non-jpg file found in "+ str(raw_dir) +
                                 ": " + str(file))
            else:
                raw_dimensions[leaf] = {}
                raw_dimensions[leaf]['width'], raw_dimensions[leaf]['height'] = Image.open(file).size
        raw_images.sort()
        return raw_images, raw_dimensions


    @staticmethod
    def load_settings(path, args=None):
        settings_file = path + '/settings.yaml'
        try:
            stream = file(settings_file, 'r')
            settings = yaml.load(stream)
        except:
            Environment.write_settings(path, Environment.settings)
            return Environment.settings
        if args:
            if args.respawn:
                settings['respawn'] = True
            elif args.no_respawn:
                settings['respawn'] = False
            if args.make_cornered_scaled is not None:
                settings['make_cornered_scaled'] = args.make_cornered_scaled
            if args.draw_clusters is not None:
                settings['draw_clusters'] = args.draw_clusters
            if args.draw_removed_clusters is not None:
                settings['draw_removed_clusters'] = args.draw_removed_clusters
            if args.draw_invalid_clusters is not None:
                settings['draw_invalid_clusters'] = args.draw_invalid_clusters
            if args.draw_content_dimensions is not None:
                settings['draw_content_dimensions'] = args.draw_content_dimensions
            if args.draw_page_number_candidates is not None:
                settings['draw_page_number_candidates'] = args.draw_page_number_candidates
            if args.draw_noise is not None:
                settings['draw_noise'] = args.draw_noise
            if args.save_settings:
                Environment.write_settings(path, settings)
        #default_settings = Environment.settings
        #for setting, value in settings.iteritems():
        #    if setting in default_settings:
        #        default_settings[setting] = value
        return settings


    @staticmethod
    def write_settings(path, settings):
        settings_file = path + '/settings.yaml'
        try:
            stream = file(settings_file, 'w')
            yaml.dump(settings,
                      stream,
                      explicit_start=True,
                      default_flow_style=False)
        except:
            print 'Failed to save settings!'


    @staticmethod
    def make_dir(dir):
        if not os.path.isdir(dir):
            try:
                os.mkdir(dir, Environment.dir_mode)
            except Exception as e:
                raise e


    @staticmethod
    def clean_dir(dir):
        if os.path.isdir(dir):
            for f in os.listdir(dir):
                if os.path.isdir(dir + '/' + f):
                    try:
                        shutil.rmtree(dir + '/' + f)
                    except Exception as e:
                        raise e
                else:
                    try:
                        os.remove(dir + '/' + f)
                    except Exception as e:
                        raise e


class BookData:

    def __init__(self, dir, raw_data):
        self.root_dir = dir
        self.identifier = os.path.basename(self.root_dir)
        self.raw_image_dir = Environment.find_raw_dir(dir)
        self.page_count = raw_data['page_count']
        self.raw_images = raw_data['images']
        self.raw_image_dimensions = raw_data['dimensions']
        self.scandata_file = self.root_dir + '/' + self.identifier + '_scandata.xml'
        self.scandata = Scandata(self.scandata_file)
        self.scaled_center_point = {}
        for leaf in range(0, self.page_count):
            self.scaled_center_point[leaf] = {'x': (self.raw_image_dimensions[leaf]['height']/
                                                    Environment.scale_factor)/2,
                                              'y': (self.raw_image_dimensions[leaf]['width']/
                                                    Environment.scale_factor)/2}
        self.dirs = {
            'book':          self.root_dir,
            'raw_images':    self.raw_image_dir,
            'logs':          self.root_dir + '/' + self.identifier + '_logs',
            'scaled':        self.root_dir + '/' + self.identifier + '_scaled',
            }

        for name, dir in self.dirs.items():
            if not os.path.exists(dir):
                Environment.make_dir(dir)


        self.logs = {
            'global': {
                'file': str(self.dirs['logs']) + '/' + self.identifier + '_global_log.txt'
                },
            'processing': {
                'file': str(self.dirs['logs']) + '/' + self.identifier + '_processing_log.txt'
                },
            'featureDetection': {
                'file': str(self.dirs['logs']) + '/' + self.identifier + '_featureDetection_log.txt'
                }
        }

        """

            'pageDetection': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_3_pageDetection_log.txt'
                },
            'fastCornerDetection': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_4_fastCornerDetection_log.txt'
                },
            'clusterAnalysis': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_5_clusterAnalysis_log.txt'
                },
            'noiseAnalysis': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_6_noiseAnalysis_log.txt'
                },
            'pagination': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_7_pagination_log.txt'
                },
            'derivation': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_8_derivation_log.txt'
                },
            'ocr': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_9_ocr_log.txt'
                }
            }
            """

    def add_dirs(self, dirs):
        for name, dir in dirs.items():
            if not os.path.isdir(dir):
                try:
                    Environment.make_dir(dir)
                except Exception as e:
                    raise e
            self.dirs[name] = dir


    def clean_dirs(self):
        for name, dir in self.dirs.items():
            if name in ('book', 'raw_images', 'logs'):
                pass
            else:
                try:
                    Environment.clean_dir(dir)
                except Exception as e:
                    raise e


    def init_logs(self, mode='w'):
        for log, key in self.logs.items():
            if log not in self.logger.logs:
                try:
                    self.logger.logs[log] = open(key['file'], mode, 1)
                except IOError:
                    Util.bail("could not open " + str(key['file']) + ' in mode ' + mode)


    def init_crops(self):
        import_scandata = True if not self.settings['respawn'] else False
        self.pageCrop = Crop('pageCrop', self.page_count,
                             self.raw_image_dimensions,
                             self.scandata, import_scandata)
        self.standardCrop = Crop('standardCrop', self.page_count,
                                 self.raw_image_dimensions,
                                 self.scandata, import_scandata)
        self.contentCrop = Crop('contentCrop', self.page_count,
                                self.raw_image_dimensions,
                                self.scandata)
        self.crops = {'pageCrop': self.pageCrop,
                      'standardCrop': self.standardCrop,
                      'contentCrop': self.contentCrop}


    def import_crops(self):
        self.cropBox = Crop('cropBox', self.page_count,
                             self.raw_image_dimensions,
                             self.scandata, True)
        self.pageCrop = Crop('pageCrop', self.page_count,
                             self.raw_image_dimensions,
                             self.scandata, True)
        self.standardCrop = Crop('standardCrop', self.page_count,
                                 self.raw_image_dimensions,
                                 self.scandata, True)
        self.contentCrop = Crop('contentCrop', self.page_count,
                                self.raw_image_dimensions,
                                self.scandata, True)
        self.crops = {'cropBox': self.cropBox,
                      'pageCrop': self.pageCrop,
                      'standardCrop': self.standardCrop,
                      'contentCrop': self.contentCrop}



class Scandata:

    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.tree = None
        try:
            self.file = open(filename, 'r+')
            parser = etree.XMLParser(remove_blank_text=True)
            self.tree = etree.parse(self.file, parser)
        except:
            pass
        else:
            self.file.close()


    def new(self, identifier, page_count,
            raw_image_dimensions,
            scandata_file):
        root = etree.Element('book')
        book_data = etree.SubElement(root,'bookData')
        book_id = etree.SubElement(book_data,'bookId')
        book_id.text = str(identifier)
        leaf_count = etree.SubElement(book_data,'leafCount')
        leaf_count.text = str(page_count)

        page_data = etree.SubElement(root, 'pageData')
        for leaf in range(0, page_count):
            side  = 'LEFT' if leaf%2==0 else 'RIGHT'
            page = etree.SubElement(page_data, 'page')
            page.set('leafNum', str(leaf))
            handside = etree.SubElement(page, 'handSide')
            handside.text = str(side)
            page_type = etree.SubElement(page, 'pageType')
            page_type.text = 'Normal' if leaf in range(1, page_count-1) else 'Delete'
            ataf = etree.SubElement(page, 'addToAccessFormats')
            ataf.text = 'true' if leaf in range(1, page_count-1) else 'false'
            rotate_degree = etree.SubElement(page, 'rotateDegree')
            rotate_degree.text = '-90' if leaf%2==0 else '90'
            skew_angle = etree.SubElement(page, 'skewAngle')
            skew_angle.text = '0.0'
            skew_conf = etree.SubElement(page, 'skewConf')
            skew_conf.text = '0.0'
            skew_active = etree.SubElement(page, 'skewActive')
            skew_active.text = 'False'
            orig_width = etree.SubElement(page, 'origWidth')
            orig_width.text = str(raw_image_dimensions[leaf]['width'])
            orig_height = etree.SubElement(page, 'origHeight')
            orig_height.text = str(raw_image_dimensions[leaf]['height'])
            crop_box = Crop.new_crop_element(page, 'cropBox')
            page_number = etree.SubElement(page, 'pageNumber')
        doc = etree.ElementTree(root)
        try:
            scandata = open(scandata_file,"w")
            doc.write(scandata, pretty_print=True)
            self.tree = doc
            scandata.close()
        except IOError:
            Util.bail('failed to make scandata for ' + identifier)



class Logger:

    def __init__(self):
        self.logs = {}

    def message(self, message, log='global'):
        if message is None:
            return
        timestamp = datetime.datetime.now()
        if type(log) == tuple:
            for l in log:
                self.logs[l].write(str(timestamp) + ':  '+ message + "\n")
        else:
            self.logs[log].write(str(timestamp) + ':  '+ message + "\n")
