#!/usr/bin/env python

# Doc: https://coddingtonbear.github.io/obsidian-local-rest-api/#/

import logging as logging
import os
from datetime import datetime
from typing import Any, Dict, List

from requests import Request, Session
from requests.exceptions import HTTPError
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
import json

""" Logger set up """
# Set up a logger to log info to console and all messages to a log file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Get current working directory and create a new folder called log to save log files
dir_path = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(dir_path + "/logs"):
    os.makedirs(dir_path + "/logs")

logfile = (
    f'{dir_path}/logs/obsidian_api_{datetime.now().strftime("%H_%M_%d_%m_%Y")}.log'
)

logging.basicConfig(
    filename=logfile,
    level=logging.DEBUG,
    format="[%(asctime)s]%(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
    filemode="w",
)

# Set up logging to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# Set a format which is simpler for console use
formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
console.setFormatter(formatter)
# Add the handler to the root logger
logging.getLogger("").addHandler(console)
logger = logging.getLogger(__name__)

disable_warnings(InsecureRequestWarning)


class ObsidianFiles:
    def __init__(
        self,
        api_url: str,
        token: str,
        public_cert: str or None = None,
        public_key: str or None = None,
    ):
        self.api_url = api_url
        self.token = token
        self.headers = {
            "accept": "text/markdown",
            "Authorization": f"Bearer {self.token}",
        }

        self.cert = (
            (public_cert, public_key) if public_cert and public_key else None
        )  # certifi.where()

    def _send_request(self, method: str, cmd: str, data: str or None = None) -> str:
        """Send an HTTP request to your local Obsidian server

        Args:
            method (str): HTTP method to send. Must be one of the following methods:
            - POST, GET, DELETE, PATCH, PUT
            cmd (str): Endpoint command to send. Must be one of the following endpoints:
            - active, vault, periodic, commands, search, open
            data (str or None, optional): Content to add to the target file. Defaults to None.

        Returns:
            str: The content in markdown format.
        """
        s = Session()
        _request = (
            Request(
                method,
                f"{self.api_url}{cmd}",
                headers=self.headers,
                data=data,
            )
            if data
            else Request(
                method,
                f"{self.api_url}{cmd}",
                headers=self.headers,
            )
        )
        prepped = s.prepare_request(_request)
        resp = (
            s.send(prepped, cert=self.cert)
            if self.cert
            else s.send(prepped, verify=False)
        )
        return resp

    ### For Active files request! ###
    def _get_active_file_content(self) -> str:
        """Returns the content of the currently active (open) file in Obsidian
        in markdown format.

        """
        try:
            resp = self._send_request("GET", cmd="/active/")
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Success!")
            return resp.text  # in text/markdown format
        except HTTPError as err:
            logging.error(err)
            return None

    def _append_content_to_active_file(self, content: str):
        """Appends content to the end of the currently-open note.

        Args:
            content (str): the content to append
        """
        self.headers["accept"] = "*/*"
        try:
            resp = self._send_request("POST", cmd="/active/", data=content)
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Added content successfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    def _update_content_of_active_file(self, content: str):
        """Update content of the currently-open note.

        Args:
            content (str): the content to update (replace) for the current active note
        """
        try:
            resp = self._send_request("POST", cmd="/active/", data=content)
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Updated content successfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    def _delete_active_file(self):
        """Delete the currently active file in Obsidian"""
        try:
            resp = self._send_request("DELETE", cmd="/active/")
            resp.raise_for_status()
            if resp.status_code == 204:
                logger.info("Deleted the currently active file in Obsidian.")
        except HTTPError as err:
            logging.error(err)
            return None

    def _insert_content_of_active_file(
        self,
        content: str,
        heading: str,
        insert_position: str,
        heading_boundary: str = "",
    ):
        """Insert content into the currently-open note
        relative to a heading within that note.

        This is useful if you have a document having multiple headings,
        and you would like to insert content below one of those headings.

        By default, this will find the first heading matching the name you specify.

        Args:
            content: the content to insert.

            heading: name of heading relative to which you would like your content inserted.
            May be a sequence of nested headers delimited by "::".

            insert_position: position at which you would like your content inserted;
            Valid options are "end" or "beginning".

            heading_boundary: set the nested header delimiter to a different value.
            This is useful if "::" exists in one of the headers you are attempting to use.

        """
        # set the header parameters
        self.headers["accept"] = "*/*"
        self.headers["Heading"] = heading
        self.headers["Content-Insertion-Position"] = insert_position
        self.headers["Content-Type"] = "text/markdown"
        if heading_boundary != "":
            self.headers["Heading-Boundary"] = heading_boundary

        try:
            resp = self._send_request("PATCH", cmd="/active/", data=content)
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Inserted the content successfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    ### Target files in your vault ###
    def _get_target_file_content(
        self,
        target_filename: str,
        return_format: str = "text/markdown",  # ]
    ) -> Dict[str, Any]:
        """
        Return the content of the file at the specified path
        in your vault should the file exist.

        Args:
            target_filename (str): path to the file to return (relative to your vault root).
            return_format (str): Returned format of the content.
            Default is 'text/markdown,
            can be set to 'json' to get frontmatter, tags, and stats.
        """
        if return_format == "json":
            self.headers["accept"] = "application/vnd.olrapi.note+json"

        try:
            resp = self._send_request("POST", cmd=f"/vault/{target_filename}")
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info(f"Got the content of {target_filename} successfully!")
                return resp.text if return_format == "text/markdown" else resp.json()
        except HTTPError as err:
            logging.error(err)
            return None

        return resp.json() if return_format == "json" else resp

    def _create_or_update_file(self, target_filename: str, content: str):
        """Create a new file in your vault or
        update the content of an existing one if the specified file already exists.

        Args:
            target_filename (str): path to the file to return (relative to your vault root).
            content (str): the content to insert.
        """
        self.headers["accept"] = "*/*"
        try:
            resp = self._send_request(
                "PUT", cmd=f"/vault/{target_filename}", data=content
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info(f"Updated {target_filename} successfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    def _delete_target_file(self, target_filename: str):
        """Delete a target file in your Obsidian vault.

        Args:
            target_filename (str): path to the file to return (relative to your vault root).

        """
        try:
            resp = self._send_request("DELETE", cmd="/active/")
            resp.raise_for_status()
            if resp.status_code == 204:
                logger.info(f"Deleted {target_filename} in Obsidian.")
        except HTTPError as err:
            logging.error(err)
            return None

    def _append_content_to_target_file(self, target_filename: str, content: str):
        """
        Appends content to the end of the target note.
        If the specified file does not yet exist, it will be created as an empty file.
        """
        self.headers["accept"] = "*/*"
        try:
            resp = self._send_request(
                "PUT", cmd=f"/vault/{target_filename}", data=content
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info(f"Updated {target_filename} successfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    def _insert_content_of_target_file(
        self,
        target_filename: str,
        content: str,
        heading: str,
        insert_position: str,
        heading_boundary: str = "",
    ):
        """Inserts content into a target note
        relative to a heading within that note.

        This is useful if you have a document having multiple headings,
        and you would like to insert content below one of those headings.

        By default, this will find the first heading matching the name you specify.

        Args:
            target_filename (str): The filename of the target note to insert to.

            content (str): the content to insert.

            heading: name of heading relative to which you would like your content inserted.
            May be a sequence of nested headers delimited by "::".

            insert_position: position at which you would like your content inserted;
            Valid options are "end" or "beginning".

            heading_boundary: set the nested header delimiter to a different value.
            This is useful if "::" exists in one of the headers you are attempting to use.

        """
        # set the header parameters
        self.headers["accept"] = "*/*"
        self.headers["Heading"] = heading
        self.headers["Content-Insertion-Position"] = insert_position
        self.headers["Content-Type"] = "text/markdown"
        if heading_boundary != "":
            self.headers["Heading-Boundary"] = heading_boundary

        try:
            resp = self._send_request(
                "PATCH", cmd=f"/vault/{target_filename}", data=content
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info(f"Inserted content to {target_filename} successfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    def _delete_target_file(self, target_filename: str):
        """Delete target file from the vault.

        Args:
            target_filename (str): The target file to delete from the vault.

        """
        self.headers["accept"] = "*/*"
        try:
            resp = self._send_request("DELETE", cmd=f"/vault/{target_filename}")
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info(f"Deleted {target_filename} successfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    ### Value Directoryies ###

    def _list_files_in_vault(self, target_dir: str) -> Dict[str, any]:
        """Lists files in the target directory of your vault.

        Args:
            target_dir (str): Path to list files from (relative to your vault root).
            Note that empty directories will not be returned.


        Returns:
            Dict[str, any]: All the files in the target directory in JSON format.

        """
        try:
            self.headers["accept"] = "application/json"
            resp = self._send_request(
                "GET",
                cmd=f"/vault/{target_dir}",
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info(f"Got the list of files in {target_dir} successfully!")
                return resp.json()
        except HTTPError as err:
            logging.error(err)
            return None

    ### Commands ###
    def _list_commands(self) -> Dict[str, any]:
        """Lists all available commands in Obsidian.

        Returns:
            Dict[str, any]: All the available commands in Obsidian in JSON format.

        """
        try:
            self.headers["accept"] = "application/json"
            resp = self._send_request(
                "GET",
                cmd="/commands/",
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Fetched all the commands successfully!")
                return resp.json()
        except HTTPError as err:
            logging.error(err)
            return None

    def _run_command(self, command_id: str) -> Dict[str, any]:
        """Lists all available commands in Obsidian.

        Args:
            command_id (str): The ID of the command to execute.
            Can be retrieved using `_list_commands` function

        Returns:
            Dict[str, any]: All the available commands in Obsidian in JSON format.

        """
        try:
            self.headers["accept"] = "*/*"
            resp = self._send_request(
                "POST",
                cmd=f"/commands/{command_id}",
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("The command is executed sucessfully!")
        except HTTPError as err:
            logging.error(err)
            return None

    ### Search ###
    def _search_with_query(self, request_body: str or dict) -> List[dict[str, any]]:
        """Search for documents matching a specificed search query.
        Evaluates a provided query against each file in your vault.
        This endpoint supports multiple query formats, including:
        - Dataview DQL
        - Json
        Your query should be specified in your request's body,
        and will be interpreted according to the Content-type header
        you specify from the below options.


        Dataview DQL (application/vnd.olrapi.dataview.dql+txt)
        Accepts a TABLE-type Dataview query as a text string.
        See Dataview's query documentation for information on how to construct a query.

        JsonLogic (application/vnd.olrapi.jsonlogic+json)
        Accepts a JsonLogic query specified as JSON.
        See JsonLogic's documentation for information about the base set of operators available,
        but in addition to those operators the following operators are available:

        glob: [PATTERN, VALUE]: Returns true if a string matches a glob pattern.
        E.g.: {"glob": ["*.foo", "bar.foo"]} is true and {"glob": ["*.bar", "bar.foo"]} is false.
        regexp: [PATTERN, VALUE]: Returns true if a string matches a regular expression.
        E.g.: {"regexp": [".*\.foo", "bar.foo"] is true and {"regexp": [".*\.bar", "bar.foo"]} is false.
        Returns only non-falsy results. "Non-falsy" here treats the following values as "falsy":

        - false
        - null or undefined
        - 0
        -[]
        - {}

        Files are represented as an object having the schema described in the Schema
        named 'NoteJson' at the bottom of this page.
        Understanding the shape of a JSON object from a schema can be tricky;
        so you may find it helpful to examine the generated metadata
        for individual files in your vault to understand exactly what values are returned.
        To see that, access the GET /vault/{filePath} route setting the header:
        Accept: application/vnd.olrapi.note+json.
        See examples below for working examples of queries
        performing common search operations.

        Args:
            request_body (str or dict): The query to use to search for file in your fault.
            Can be retrieved using `_list_commands` function

        Returns:
            List[dict[str, any]]: All the files that match the query.

        """
        try:
            self.headers["accept"] = "application/json"
            self.headers["Content-Type"] = (
                "application/vnd.olrapi.dataview.dql+txt"
                if isinstance(request_body, str)
                else "application/vnd.olrapi.jsonlogic+json"
            )

            req_body = (
                request_body
                if isinstance(request_body, str)
                else json.dumps(request_body)
            )

            resp = self._send_request("POST", cmd="/search/", data=req_body)
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Got the results!")
                return resp.json()
        except HTTPError as err:
            logging.error(err)
            return None

    def _search_with_simple_query(
        self, query: str, content_length: int = 100
    ) -> List[dict[str, any]]:
        """Search for documents matching a specificed search text query.

        Args:
            query (str): The search query to use to search for file in your fault.
            content_length (int): How much context to return around the matching string.
            Default: 100

        Returns:
            List[dict[str, any]]: Files that match the query with context.

        """
        try:
            self.headers["accept"] = "application/json"

            resp = self._send_request(
                "POST",
                cmd=f"/search/{query}&contextLength={content_length}",
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Got the results!")
                return resp.json()
        except HTTPError as err:
            logging.error(err)
            return None

    def _search_with_gui(
        self, query: str, content_length: int = 100
    ) -> List[dict[str, any]]:
        """Uses the search functionality built into the Obsidian UI to find matching files.

        Note:
            This particular method relies on interacting with the UI directly rather than
            interacting with your notes behind-the-scenes;
            so you will see the search panel open when sending requests to this API.
            As far as the developers of this library are aware, this is unavoidable.

        Args:
            query (str): The search query to use to search for file in your fault.
            Search options include:
            - path: match the path of a file
            - file: match file name
            - tag: search for tags
            - line:() search for keywords on the same line
            - section: search for keywords under the same heading
            See the search field in the Obsidian UI for a better understanding of
            what options are available.

            content_length (int): How much context to return around the matching string.
            Default: 100

        Returns:
            List[dict[str, any]]: Files that match the query with context.

        """
        try:
            self.headers["accept"] = "application/json"

            resp = self._send_request(
                "POST",
                cmd=f"/search/gui/?{query}&contextLength={content_length}",
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info("Got the results!")
                return resp.json()
        except HTTPError as err:
            logging.error(err)
            return None

    ### Open ###
    def _open_file(
        self,
        target_filename: str,
        new_leaf: bool = False,
    ) -> List[dict[str, any]]:
        """Opens the specified document in Obsidian.

        Note:
            Obsidian will create a new document at the path you have specified
            if such a document did not already exist.

        Args:
            target_filename (str): Path to the file to return (relative to your vault root).
            new_leaf (bool): Whether to open this note as a new leaf. Defaults to False.

        Returns:
            List[dict[str, any]]: Files that match the query with context.

        """
        try:
            self.headers["accept"] = "application/json"

            resp = self._send_request(
                "POST",
                cmd=f"/open/{target_filename}?newLeaf={new_leaf}",
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.info(f"Opened {target_filename} in Obsidian.")
        except HTTPError as err:
            logging.error(err)
            return None
