#
# Copyright 2015-2020 Elliot Jordan
# Based on original processor by Nick Gamewell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gzip
import json
import os
import socket

# pylint: disable=unused-import
from autopkglib import (  # noqa: F401
    APLooseVersion,
    Processor,
    ProcessorError,
    URLGetter,
    is_mac,
)

__all__ = ["GoToMeetingURLProvider"]

HOSTNAME = "builds.cdn.getgo.com"

# workaround for 10.12.x SNI issue
if is_mac():
    import platform

    # the following check is mac specific:
    if APLooseVersion(platform.mac_ver()[0]) < APLooseVersion("10.13.0"):
        # pylint: disable=no-member
        HOSTNAME = socket.gethostbyname_ex("builds.cdn.getgo.com")[0]

BASE_URL = "https://" + HOSTNAME + "/g2mupdater/live/config.json"


class GoToMeetingURLProvider(URLGetter):
    """Provides a download URL and build number for the latest GoToMeeting
    release."""

    input_variables = {
        "base_url": {
            "required": False,
            "description": "URL for the GoToMeeting "
            f"releases JSON feed. Default is {BASE_URL}.",
        }
    }
    output_variables = {
        "url": {"description": "URL to the latest GoToMeeting release."},
        "build": {"description": "Build number of the latest GoToMeeting release."},
    }
    description = __doc__

    def get_g2m_info(self, base_url):
        """Process the JSON data from the latest release."""

        # Prepare download file path.
        download_dir = os.path.join(self.env["RECIPE_CACHE_DIR"], "downloads")
        meta_path = os.path.join(download_dir, "meta")
        try:
            os.makedirs(download_dir)
        except OSError:
            # Directory already exists
            pass

        # Download JSON feed (or gzipped JSON feed) to a file.
        meta_file = self.download_to_file(base_url, meta_path)

        # Sometimes the base URL is compressed as gzip, sometimes it's not.
        try:
            with open(meta_file, "rb") as f:
                jsondata = json.loads(f.read())
                self.output("Encoding: json")
        except ValueError:
            with gzip.open(meta_file, "rb") as f:
                jsondata = json.loads(f.read())
                self.output("Encoding: gzip")

        max_build = max(jsondata["activeBuilds"], key=lambda x: int(x["buildNumber"]))
        g2m_url = max_build.get("macDownloadUrl")
        if not g2m_url:
            raise ProcessorError(
                "No download URL for the latest release "
                "found in the base_url JSON feed."
            )
        url_parts = g2m_url.split("/")
        url_parts[-1] = "GoToMeeting.dmg"
        g2m_url = "/".join(url_parts)

        g2m_build = str(max_build["buildNumber"])

        return g2m_url, g2m_build

    def main(self):
        """Main process."""

        base_url = self.env.get("base_url", BASE_URL)
        g2m_url, g2m_build = self.get_g2m_info(base_url)
        self.env["url"] = g2m_url
        self.output(f"Found URL: {self.env['url']}")
        self.env["build"] = g2m_build
        self.output(f"Build number: {self.env['build']}")


if __name__ == "__main__":
    PROCESSOR = GoToMeetingURLProvider()
    PROCESSOR.execute_shell()
