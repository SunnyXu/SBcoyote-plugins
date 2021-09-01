import importlib.abc
import importlib.util
import inspect
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, cast
import logging
import inspect
import traceback
import json
from pprint import pprint

from rkviewer.plugin.classes import CommandPlugin, Plugin, PluginCategory, PluginType, WindowedPlugin

def wrap_exception(pname, method):
    def ret(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            errmsg = ''.join(traceback.format_exception(None, e, e.__traceback__))
            errmsg = "Caught error in plugin '{}':\n".format(pname) + errmsg
            print(errmsg)
    return ret

def extract_meta():
  dir_path = "all-plugins"

  if not os.path.exists(dir_path):
    return False

  plugin_classes = list()
  plugin_metadata = dict()
  for f in os.listdir(dir_path):
    print(f)
    if not f.endswith('.py'):
      continue
    mod_name = '_rkviewer.plugin_{}'.format(f[:-2])  # remove extension
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(dir_path, f))
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    loader = cast(importlib.abc.Loader, spec.loader)

    try:
        loader.exec_module(mod)
    except Exception as e:
        except_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        errmsg = "Failed to load plugin '{}':\n{}".format(f, except_str)
        print(errmsg)
        continue

    def pred(o): return o.__module__ == mod_name and issubclass(o, Plugin)

    cur_classes = [m[1] for m in inspect.getmembers(mod, inspect.isclass) if pred(m[1])]
    for cls in cur_classes:
        if inspect.isabstract(cls):
            logging.warning("Plugin in file '{}' is an abstract class. Did not load.".format(f))
            continue

        if not hasattr(cls, 'metadata'):
            logging.warning("Plugin in file '{}' does not have a `metadata` class attribute. "
                "Did not load. See plugin documentation for more information.".format(f))
            continue

        for method_name, method in inspect.getmembers(cls, inspect.isroutine):
            setattr(cls, method_name, wrap_exception(cls.metadata.name, method))

        plugin_classes.append(cls)
        m_fields = dict()
        m = cls.metadata
        m_fields.update({'name': m.name})
        m_fields.update({'author': m.author})
        m_fields.update({'category': str(m.category)})
        m_fields.update({'long_desc': m.long_desc})
        m_fields.update({'short_desc': m.short_desc})
        m_fields.update({'version': m.version})
        plugin_metadata.update({f: m_fields})

  return plugin_metadata

def write_meta(plugin_metadata, metadata_path):
    pprint(plugin_metadata)
    with open(metadata_path, 'w') as f:
        json.dump(plugin_metadata, f)
        f.close()

def main():
  plugin_metadata = extract_meta()
  metadata_path = "metadata.json"
  write_meta(plugin_metadata, metadata_path)

if __name__ == '__main__':
  main()