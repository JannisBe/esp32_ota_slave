# 1000 x dank aan Evelien die mijn in deze tijden gesteund heeft
# ohja, en er is ook nog tante suker (Jana Dej.) die graag kinderen wilt maar het zelf nog niet beseft

import os
import gc
import machine
from .HttpUtility import Response, HttpClient
import time
import network

class OTAUpdater:

    def __init__(self, github_repo, module='', main_dir='src', headers={}, skipped_files=[], wifi_timeout=10, logger=None):
        self.http_client = HttpClient(headers=headers)
        self.github_repo = github_repo.rstrip('/').replace('https://github.com', 'https://api.github.com/repos')
        self.main_dir = main_dir
        self.module = module.rstrip('/')
        self.skipped_files = skipped_files
        self.wifi_timeout = wifi_timeout
        self.logger = logger

    def check_for_update_to_install_during_next_reboot(self):
        current_version = self.get_version(self.modulepath(self.main_dir))
        latest_version = self.get_latest_version()

        if latest_version > current_version:
            self.logger.log('New version available', nodisplay=True)
            try:
                os.mkdir(self.modulepath('next'))
            except:
                pass
            with open(self.modulepath('next/.version_on_reboot'), 'w') as versionfile:
                versionfile.write(latest_version)
                versionfile.close()
                return True
        return False

    def download_and_install_update_if_available(self):
        self.check_for_update_to_install_during_next_reboot()
        if 'next' in os.listdir(self.module):
            if '.version_on_reboot' in os.listdir(self.modulepath('next')):
                latest_version = self.get_version(self.modulepath('next'), '.version_on_reboot')
                self.logger.log('New update found: {0}'.format(latest_version), nodisplay=True)
                self._download_and_install_update(latest_version)
        else:
            self.logger.log('No new updates found...', nodisplay=True)

    def _download_and_install_update(self, latest_version):


        self.download_all_files(self.github_repo + '/contents/')
        self.rmtree(self.modulepath(self.main_dir))
        os.rename(self.modulepath('next/.version_on_reboot'), self.modulepath('next/.version'))
        os.rename(self.modulepath('next'), self.modulepath(self.main_dir))
        self.logger.log('Update installed ({0}), will reboot now'.format(latest_version), nodisplay=True)
        machine.reset()

    def apply_pending_updates_if_available(self):
        if 'next' in os.listdir(self.module):
            if '.version' in os.listdir(self.modulepath('next')):
                pending_update_version = self.get_version(self.modulepath('next'))
                self.logger.log('Pending update found: {0}'.format(pending_update_version), nodisplay=True)
                self.rmtree(self.modulepath(self.main_dir))
                os.rename(self.modulepath('next'), self.modulepath(self.main_dir))
            else:
                self.logger.log('Corrupt pending update found, discarding...', nodisplay=True)
                self.rmtree(self.modulepath('next'))
        else:
            self.logger.log('No pending update found', nodisplay=True)

    def download_updates_if_available(self):
        current_version = self.get_version(self.modulepath(self.main_dir))
        latest_version = self.get_latest_version()

        if latest_version > current_version:
            os.mkdir(self.modulepath('next'))
            self.download_all_files(self.github_repo + '/contents/')
            with open(self.modulepath('next/.version'), 'w') as versionfile:
                versionfile.write(latest_version)
                versionfile.close()

            return True
        return False

    def rmtree(self, directory):
        for entry in os.ilistdir(directory):
            is_dir = entry[1] == 0x4000
            if is_dir:
                self.rmtree(directory + '/' + entry[0])

            else:
                os.remove(directory + '/' + entry[0])
        os.rmdir(directory)

    def get_version(self, directory, version_file_name='.version'):
        if version_file_name in os.listdir(directory):
            f = open(directory + '/' + version_file_name)
            version = f.read()
            f.close()
            return version
        return '0.0'

    def get_latest_version(self):
        latest_release = self.http_client.get(self.github_repo + '/commits')
        version = latest_release.json()[0]['sha']
        latest_release.close()
        return version

    def download_all_files(self, root_url):
        file_list = self.http_client.get(root_url)
        self.logger.log("{0}".format(root_url), nodisplay=True)
        for file in file_list.json():
            if file['name'] not in self.skipped_files:
                if file['type'] == 'file':
                    download_url = file['download_url']
                    download_path = self.modulepath('next/' + file['path'].replace(self.main_dir + '/', ''))
                    self.logger.log('download_path: {0}'.format(download_path), nodisplay=True)
                    self.download_file(download_url.replace('refs/tags/', ''), download_path)
                elif file['type'] == 'dir':
                    path = self.modulepath('next/' + file['path'].replace(self.main_dir + '/', ''))
                    try:
                        os.mkdir(path)
                    except OSError:
                        pass
                    if root_url[-1] == '/':
                        self.download_all_files(root_url + file['name'])
                    else:
                        self.download_all_files(root_url + '/' + file['name'])
        file_list.close()

    def download_file(self, url, path):
        with open(path, 'wb+') as outfile:
            try:
                response = self.http_client.get(url)
                for t in response.text:
                    outfile.write(t)
            finally:
                try:
                    response.close()
                except:
                    pass
                outfile.close()
                gc.collect()

    def modulepath(self, path):
        return self.module + '/' + path if self.module else path
