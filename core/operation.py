
class Operation(object):
    """
    Base Class for processing operations.

    """


    def __init__(self, components):
        try:
            self.__import_components(components)
        except ImportError:
            raise ImportError('Failed to import components')
        self.completed = {}
        self.exec_times = []


    def __import_components(self, components):
        for component, _class  in components.items():
            globals()[_class] = __import__('components.'+component,
                                           globals(), locals(),
                                           [_class,], -1)
        self.imports = components


    def init_components(self, args):
        self.components = []
        for component, _class in self.imports.items():
            instance = getattr(globals()[_class], _class)(args.pop(0))
            self.components.append(instance)
            setattr(self, _class, instance)


    def complete_process(self, leaf, exec_time):
        self.completed[leaf] = exec_time
        self.exec_times.append(exec_time)


    def get_avg_exec_time(self):
        return sum(self.exec_times)/len(self.exec_times)
