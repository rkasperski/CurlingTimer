from Logger import warning
from pathlib import Path
import os
import shutil


class AppSetup:
    def __init__(self, appName, user=None, group=None, configDir="config", dataDir="data", updateDir="update", configOnExternalMedia=False, dataOnExternalMedia=False, updateOnExternalMedia=False, externalPath=None):
        self.__appName = appName.replace('/', '-')
        self.__user = user
        self.__group = group
        
        self.__appPath = os.path.dirname(os.path.realpath(__file__))
        self.__homePath = self.__getHomePath()
        self.__workingPath = self.__getWorkingPath()
        self.__dataPath = self.__getPath(dataDir, dataOnExternalMedia, externalPath)
        self.__configPath = self.__getPath(configDir, configOnExternalMedia, externalPath)
        self.__updatePath = self.__getPath(updateDir, updateOnExternalMedia, externalPath)

    def dump(self):
        print(f"""AppSetup
        appName={self.name}
        user={self.user}
        group={self.group}
        appDir={self.appDir}
        homeDir={self.homeDir}
        workinDir={self.workingDir}
        dataDir={self.dataDir}
        configDir={self.configDir}
        updateDir={self.updateDir}""")

    @property
    def name(self):
        return self.__appName

    @property
    def user(self):
        return self.__user

    @property
    def group(self):
        return self.__group

    @property
    def appDir(self):
        return self.__appPath
    
    @property
    def homeDir(self):
        return self.__homePath
    
    @property
    def workingDir(self):
        return self.__workingPath
    
    @property
    def dataDir(self):
        return self.__dataPath
    
    @property
    def configDir(self):
        return self.__configPath
    
    @property
    def updateDir(self):
        return self.__updatePath
    
    def __join(self, dir, fn, createDir=True):
        path = os.path.join(dir, fn) if fn else dir

        if createDir:
            if fn is not None and not fn.endswith("/"):
                dir = os.path.dirname(path)
            else:
                dir = path
                
            if not os.path.exists(dir):
                os.makedirs(dir)
                shutil.chown(dir, user=self.__user, group=self.__group)

        return path
    
    def home(self, dir=None, createDir=True):
        return self.__join(self.__homePath, dir)
    
    def working(self, dir=None, createDir=True):
        return self.__join(self.__workingPath, dir, createDir=createDir)
    
    def data(self, dir=None, createDir=True):
        return self.__join(self.__dataPath, dir, createDir=createDir)
    
    def update(self, dir=None, createDir=True):
        return self.__join(self.__updatePath, dir, createDir=createDir)
    
    def config(self, dir=None, createDir=True):
        return self.__join(self.__configPath, dir, createDir=createDir)
    
    def app(self, dir=None, createDir=True):
        return self.__join(self.__appPath, dir, createDir=createDir)
    
    def __getHomePath(self):
        if self.__user:
            home = os.path.expanduser('~' + self.__user)
        else:
            home = str(Path.home())

        return home

    def __getWorkingPath(self):
        return os.getcwd()
    
    def __getPath(self, dirName, onExternalMedia, externalPath):
        dirPath = None
        if onExternalMedia:
            externalPath = os.path.join("/media", self.__user, self.__appName) if externalPath is None else externalPath

            if os.path.exists(externalPath):
                dirPath = externalPath

        if not dirPath:
            dirPath = os.environ.get(self.__appName.upper() + "_HOME")

        if not dirPath:
            dirPath = os.path.join(self.__homePath, dirName)

        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
            shutil.chown(dirPath, user=self.__user, group=self.__group)
        
        dirPath = os.path.join(dirPath, self.__appName, dirName)

        if not os.path.isdir(dirPath):
            os.makedirs(dirPath)
            shutil.chown(dirPath, user=self.__user, group=self.__group)

        return dirPath
    
    def copyFile(self, fn, srcPath=None, tgtPath=None):
        srcPath = srcPath if srcPath else app.app()
        tgtPath = tgtPath if tgtPath else app.working()
        
        if not os.path.exists(tgtPath):
            os.makedirs(tgtPath)
            shutil.chown(tgtPath, user=self.__user, group=self.__group)

        src = os.path.join(srcPath, fn)
        tgt = os.path.join(tgtPath, fn)
    
        if not os.path.exists(tgt):
            warning("setup: copying setup file: %s to %s", src, tgt)
            shutil.copyfile(src, tgt)
            shutil.chown(tgt, user=self.__user, group=self.__group)

    def copyFiles(self, requiredFiles, srcDir, tgtDir):
        for fn in requiredFiles:
            self.copyFile(fn, srcDir, tgtDir)

            
app = None


def setApp(appP):
    global app

    app = appP

    
def getApp():
    return app


if __name__ == "__main__":
    app = AppSetup("splog", user="pi", group="pi")
    app.copyFiles((("config.toml", "defaults", None),))
