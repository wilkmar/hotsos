from hotsos.core import plugintools


class StorageBase(plugintools.PluginPartBase):
    """ Base class for all storage checks. """
    plugin_name = 'storage'
    plugin_root_index = 9

    @classmethod
    def is_runnable(cls):
        raise NotImplementedError
