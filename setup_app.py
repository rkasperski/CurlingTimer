"""
Implements routines to assist in the consistent placement of
configuration files and provide consistent accesss to
directories where the app and it's data is stored.
"""
from pathlib import Path
import os
import shutil
from logger import warning


class AppSetup:
    def __init__(self, app_name,
                 user=None,
                 group=None,
                 config_dir="config",
                 data_dir="data",
                 update_dir="update",
                 config_on_external_media=False,
                 data_on_external_media=False,
                 update_on_external_media=False,
                 external_path=None):
        self.__app_name = app_name.replace('/', '-')
        self.__user = user
        self.__group = group
        self.__app_path = os.path.dirname(os.path.realpath(__file__))
        self.__home_path = self.__get_home_path()
        self.__working_path = self.__get_working_path()
        self.__data_path = self.__get_path(data_dir, data_on_external_media, external_path)
        self.__config_path = self.__get_path(config_dir, config_on_external_media, external_path)
        self.__update_path = self.__get_path(update_dir, update_on_external_media, external_path)

    def dump(self):
        print(f"""AppSetup
        app_name={self.name}
        user={self.user}
        group={self.group}
        app_dir={self.app_dir}
        home_dir={self.home_dir}
        working_dir={self.working_dir}
        data_dir={self.data_dir}
        config_dir={self.config_dir}
        update_dir={self.update_dir}""")

    @property
    def name(self):
        return self.__app_name

    @property
    def user(self):
        return self.__user

    @property
    def group(self):
        return self.__group

    @property
    def app_dir(self):
        return self.__app_path

    @property
    def home_dir(self):
        return self.__home_path

    @property
    def working_dir(self):
        return self.__working_path

    @property
    def data_dir(self):
        return self.__data_path

    @property
    def config_dir(self):
        return self.__config_path

    @property
    def update_dir(self):
        return self.__update_path

    def __join(self, dir, fn, create_dir=True):
        path = os.path.join(dir, fn) if fn else dir

        if create_dir:
            if fn is not None and not fn.endswith("/"):
                dir = os.path.dirname(path)
            else:
                dir = path

            if not os.path.exists(dir):
                os.makedirs(dir)
                shutil.chown(dir, user=self.__user, group=self.__group)

        return path

    def home(self, dir=None, create_dir=True):
        return self.__join(self.__home_path, dir)

    def working(self, dir=None, create_dir=True):
        return self.__join(self.__working_path, dir, create_dir=create_dir)

    def data(self, dir=None, create_dir=True):
        return self.__join(self.__data_path, dir, create_dir=create_dir)

    def update(self, dir=None, create_dir=True):
        return self.__join(self.__update_path, dir, create_dir=create_dir)

    def config(self, dir=None, create_dir=True):
        return self.__join(self.__config_path, dir, create_dir=create_dir)

    def app(self, dir=None, create_dir=True):
        return self.__join(self.__app_path, dir, create_dir=create_dir)

    def __get_home_path(self):
        if self.__user:
            home = os.path.expanduser('~' + self.__user)
        else:
            home = str(Path.home())

        return home

    def __get_working_path(self):
        return os.getcwd()

    def __get_path(self, dir_name, on_external_media, external_path):
        dir_path = None
        if on_external_media:
            external_path = os.path.join("/media", self.__user, self.__app_name) if external_path is None else external_path

            if os.path.exists(external_path):
                dir_path = external_path

        if not dir_path:
            dir_path = os.environ.get(self.__app_name.upper() + "_HOME")

        if not dir_path:
            dir_path = os.path.join(self.__home_path, dir_name)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            shutil.chown(dir_path, user=self.__user, group=self.__group)

        dir_path = os.path.join(dir_path, self.__app_name, dir_name)

        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
            shutil.chown(dir_path, user=self.__user, group=self.__group)

        return dir_path

    def copy_file(self, fn, src_path=None, tgt_path=None):
        src_path = src_path if src_path else app.app()
        tgt_path = tgt_path if tgt_path else app.working()

        if not os.path.exists(tgt_path):
            os.makedirs(tgt_path)
            shutil.chown(tgt_path, user=self.__user, group=self.__group)

        src = os.path.join(src_path, fn)
        tgt = os.path.join(tgt_path, fn)

        if not os.path.exists(tgt):
            warning("setup: copying setup file: %s to %s", src, tgt)
            shutil.copyfile(src, tgt)
            shutil.chown(tgt, user=self.__user, group=self.__group)

    def copy_files(self, required_files, src_dir, tgt_dir):
        for fn in required_files:
            self.copy_file(fn, src_dir, tgt_dir)


app = None


def set_app(app_p):
    global app

    app = app_p


def get_app():
    return app


if __name__ == "__main__":
    app = AppSetup("splog", user="pi", group="pi")
    app.copy_files(("config.toml", "defaults", None),
                   "test1", "test2")
