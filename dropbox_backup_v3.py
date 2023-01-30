import copy
import hashlib
import sys
import pickle
import os
import tkinter.filedialog as tkfd

import dropbox
from dropbox.exceptions import AuthError
from dropbox.files import FileMetadata, FolderMetadata
from datetime import datetime

import DB_attrib

CUSTOM_IS_FOLDER = "is_folder"


def dropbox_file_hash(filename: str):
    '''
    This implements the hashing algorithm used by Dropbox
    :param filename: name of the local file to hash
    :return:
    '''
    BUFF_SIZE = 4 * 1024 * 1024  # Dropbox reads stuff in 4 MB chunks
    with open(filename, "rb") as file:
        binary = hashlib.sha256()
        while True:
            data = file.read(BUFF_SIZE)
            if not data:
                break
            binary.update(hashlib.sha256(data).digest())
        return binary.hexdigest()


def is_good_connection(dbx: dropbox.Dropbox):
    '''
    Check that the access token is valid
    :param dbx:
    :return:
    '''
    try:
        print("Accessing the account with email: " + dbx.users_get_current_account().email)
        return True
    except AuthError:
        print("ERROR: Invalid access token; try re-generating an "
              "access token from the app console on the web.")
        return False


def files_on_server(token: str,
                    server_top_folder: str,
                    server_cache_filename=""):
    '''
    Obtain a dictionary representing all files on the dropbox server
    Store the dictionary in memory and as a file
    :param token: This is the token generated from your dropbox app console
    :param server_cache_filename: This is the name of the local file storing the dictionary
    :return:
    '''
    dict_of_files = {}

    print("Connecting to Dropbox...")
    with dropbox.Dropbox(token) as dbx:

        if not is_good_connection(dbx):
            return {}

        entries_list = []
        curr_entries = dbx.files_list_folder(server_top_folder, recursive=True)
        entries_list.append(curr_entries)
        if curr_entries.has_more:
            while True:
                curr_entries = dbx.files_list_folder_continue(curr_entries.cursor)
                entries_list.append(curr_entries)
                print("Looping through: " + curr_entries.entries[0].path_display)
                if not curr_entries.has_more:
                    break
    print("Looped through all files. Closed connection to DropBox.")

    for each_list in entries_list:
        for each_entry in each_list.entries:
            if isinstance(each_entry, FileMetadata):
                dict_of_files[each_entry.path_display.lower()] = {
                    DB_attrib.FILE_PATH_DISPLAY: each_entry.path_display,
                    DB_attrib.FILE_CLIENT_MODIFIED: each_entry.client_modified,
                    DB_attrib.FILE_SIZE: each_entry.size,
                    DB_attrib.FILE_CONTENT_HASH: each_entry.content_hash,
                    CUSTOM_IS_FOLDER: False
                }
            elif isinstance(each_entry, FolderMetadata):
                dict_of_files[each_entry.path_display.lower()] = {
                    DB_attrib.FILE_PATH_DISPLAY: each_entry.path_display,
                    CUSTOM_IS_FOLDER: True
                }
    if "" != server_cache_filename:
        try:
            pickle_dump(dict_of_files, server_cache_filename)
        except Exception as e:
            print("ERROR: Unable to save server file dictionary to the specified file: " +
                  server_cache_filename + " Exception: " + str(e))
    return dict_of_files


def pickle_dump(obj, filename: str):
    with open(filename, "wb") as out_file:
        pickle.dump(obj, out_file)


def pickle_load(filename: str):
    with open(filename, "rb") as pickle_file:
        return pickle.load(pickle_file)


def download_files(token: str,
                   download_list: list,
                   local_top_folder: str):
    '''
    :param token:
    :param download_list: download list of files on server
    :param local_top_folder:
    :return: list of files failed to sync
    Download all files in the download_list and record local filenames in the provided dict_of_files
    '''

    if len(download_list) == 0:
        return []

    if not os.path.exists(local_top_folder):
        try:
            os.makedirs(local_top_folder)
        except:
            print("ERROR: Invalid path for local_root_folder.")
            return download_list

    failed_list = []
    num_files_download = len(download_list)
    print("Connecting to Dropbox...")
    with dropbox.Dropbox(token) as dbx:

        if not is_good_connection(dbx):
            return download_list
        print("Downloading files...")

        for i in range(num_files_download):
            try:
                print("Checking [" + str(i + 1) + "/" + str(num_files_download) + "]: " + download_list[i])
                local_filename = local_top_folder + download_list[i]
                file_meta = dbx.files_get_metadata(download_list[i])

                if isinstance(file_meta, FileMetadata):
                    local_directory = os.path.dirname(local_filename)
                    if not os.path.exists(local_directory):
                        os.makedirs(local_directory)
                    print("Downloading [" + str(i + 1) + "/" + str(num_files_download) + "]: " + download_list[i])
                    dbx.files_download_to_file(local_filename, download_list[i])

                    mod_time = file_meta.client_modified.timestamp()
                    os.utime(local_filename, (mod_time, mod_time))

                else:
                    print(
                        "Creating folder for [" + str(i + 1) + "/" + str(num_files_download) + "]: " + download_list[i])
                    os.makedirs(local_filename)

            except AuthError as e:
                print("ERROR: Authentication failed. Please refresh token. Exception: " + str(e))
                sys.exit("Unable to refresh access token. Exit now.")

            except KeyboardInterrupt:
                print("Keyboard interrupt. Removing unfinished download file before exiting...")
                os.remove(local_filename)
                sys.exit("File removed. Exit.")

            except Exception as e:
                print("ERROR: Failed to download: " + download_list[i] + " . Exception: " + str(e))
                failed_list.append(download_list[i])

    return failed_list


def build_local_cache(local_top_folder: str):
    '''
    This
    :param local_top_folder:
    :return:
    '''
    local_file_dict = {}
    for root, dirs, files in os.walk(local_top_folder):
        for each_file in files:
            file_index = os.path.join(root, each_file).split(local_top_folder)[1]
            modified_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(root, each_file)))
            size = os.path.getsize(os.path.join(root, each_file))

            local_file_dict[file_index.lower()] = {
                DB_attrib.FILE_PATH_DISPLAY: file_index,
                CUSTOM_IS_FOLDER: False,
                DB_attrib.FILE_CLIENT_MODIFIED: modified_time,
                DB_attrib.FILE_SIZE: size
            }

        for each_dir in dirs:
            dir_index = os.path.join(root, each_dir).split(local_top_folder)[1]
            local_file_dict[dir_index.lower()] = {
                DB_attrib.FILE_PATH_DISPLAY: dir_index,
                CUSTOM_IS_FOLDER: True
            }
    return local_file_dict


def remove_files(remove_list: list,
                 local_file_dict: dict,
                 local_top_folder: str):
    '''
    This
    :param local_top_folder:
    :param remove_list: list of local files to remove
    :param local_file_dict: update changes to local_file_dict
    :return: list of files and folders failed to remove
    '''

    if len(remove_list) == 0:
        print("Not removing files because remove_list is empty.")
        return []

    if len(local_file_dict.keys()) == 0:
        print("Not removing files because local_file_dict is empty.")
        return remove_list

    failed = []

    print("Removing files...")
    num_files_remove = len(remove_list)
    remove_list.sort(reverse=True)

    for i in range(num_files_remove):
        try:
            print("Now removing [" + str(i + 1) + "/" + str(num_files_remove) + "]: " + remove_list[i])
            local_filename = local_top_folder + remove_list[i]
            if os.path.isfile(local_filename):
                assert not local_file_dict[remove_list[i].lower()][CUSTOM_IS_FOLDER]
                os.remove(local_filename)
                local_file_dict.pop(remove_list[i].lower())
            elif os.path.isdir(local_filename):
                assert local_file_dict[remove_list[i].lower()][CUSTOM_IS_FOLDER]
                os.rmdir(local_filename)
            else:
                print("ERROR: cannot remove: " + local_filename)
                failed.append(remove_list[i])
                # pickle_dump(failed,
                #             os.path.join(local_top_folder, "failed_to_removing.pickle"))
        except KeyboardInterrupt:
            sys.exit("Keyboard Interrupt. Exiting now.")
        except Exception as e:
            print("ERROR: failed to remove " + remove_list[i] + " Exception: " + str(e))
            failed.append(remove_list[i])

    return failed


def move_files(move_dict: dict,
               local_file_dict: dict,
               local_top_folder: str):
    '''
    This
    :param move_dict:
    :param local_top_folder:
    :param local_file_dict: update changes to local_file_dict
    :return: list of files and folders failed to remove
    '''

    if len(move_dict) == 0:
        print("Not moving files because move_dict is empty.")
        return {}

    move_list = list(move_dict.keys())
    move_list.sort(reverse=True)

    if len(local_file_dict.keys()) == 0:
        print("Not moving files because local_file_dict is empty.")
        return move_dict

    failed = {}

    print("Moving files...")

    num_files_move = len(move_list)

    for i in range(num_files_move):
        try:
            print("Now moving [" + str(i + 1) + "/" + str(num_files_move) + "]: from " + move_list[i] + " to " +
                  move_dict[move_list[i]])
            old_pathfile = local_top_folder + move_list[i]
            new_pathfile = local_top_folder + move_dict[move_list[i]]
            new_dir = os.path.dirname(new_pathfile)

            if os.path.isfile(old_pathfile) and not os.path.exists(new_dir):
                try:
                    os.makedirs(new_dir)
                except OSError:
                    print(
                        "ERROR: Unable to create folder for: " + move_list[i] + " at the new location: " + new_pathfile)
                    failed[move_list[i]] = move_dict[move_list[i]]
                    continue

            os.rename(old_pathfile, new_pathfile)
            local_file_dict[move_dict[move_list[i]].lower()] = local_file_dict.pop(move_list[i].lower())


        except KeyboardInterrupt:
            sys.exit("Keyboard Interrupt. Exiting now.")
        except Exception as e:
            print("ERROR: cannot move " + move_list[i] + " Exception: " + str(e))
            failed[move_list[i]] = move_dict[move_list[i]]

    return failed


def resolve_difference(server_dict: dict,
                       local_dict: dict,
                       local_top_folder: str):
    '''
    Note all keys in server_dict and local_dict are in lower cases
    :param server_dict:
    :param local_dict:
    :param local_top_folder:
    :return:
    '''
    server_files = list(server_dict.keys())
    local_files = list(local_dict.keys())

    download_list = []
    remove_list = []

    for each_file in local_files:
        if each_file not in server_dict.keys():
            remove_list.append(local_dict[each_file][DB_attrib.FILE_PATH_DISPLAY])
        else:
            if local_dict[each_file][CUSTOM_IS_FOLDER]:
                server_files.remove(each_file)
            else:
                if server_dict[each_file][DB_attrib.FILE_CLIENT_MODIFIED] <= local_dict[each_file][
                    DB_attrib.FILE_CLIENT_MODIFIED]:
                    server_files.remove(each_file)

    download_list.extend(server_files)

    print(download_list)
    print(remove_list)

    download_hash = {}
    move_map = {}

    if len(remove_list) > 0:
        for each_file in download_list:
            if not server_dict[each_file][CUSTOM_IS_FOLDER]:
                file_hash = server_dict[each_file][DB_attrib.FILE_CONTENT_HASH]
                if file_hash not in download_hash.keys():
                    download_hash[file_hash] = [each_file]
                else:
                    download_hash[file_hash].append(each_file)

        remove_list_copy = copy.deepcopy(remove_list)
        for each_file in remove_list_copy:
            local_path_name = local_top_folder + each_file
            if os.path.isfile(local_path_name):
                file_hash = dropbox_file_hash(local_path_name)
                if file_hash in download_hash.keys():
                    if len(download_hash[file_hash]) <= 0:
                        continue
                    new_file_lower = download_hash[file_hash].pop()
                    new_file_pathname = server_dict[new_file_lower][DB_attrib.FILE_PATH_DISPLAY]
                    move_map[each_file] = new_file_pathname
                    download_list.remove(new_file_lower)
                    remove_list.remove(each_file)

    return [server_dict[x][DB_attrib.FILE_PATH_DISPLAY] for x in download_list], \
           remove_list, \
           move_map


def get_valid_token():
    while True:
        current_token = input("Please copy and paste the token below: \n")
        with dropbox.Dropbox(current_token) as dbx:
            if is_good_connection(dbx):
                print("Token validated.")
                return current_token
            else:
                usr_input = input("Invalid token. Try again? (y/n)")
                if "n" == usr_input:
                    return ""
                else:
                    if "y" == usr_input:
                        continue
                    print("Invalid response. Trying again.")


def get_valid_server_top_folder(current_token: str):
    while True:
        with dropbox.Dropbox(current_token) as dbx:
            if not is_good_connection(dbx):
                sys.exit("Token invalid. Please update token. Exit now.")

            top_folder = input("Please input your dropbox top folder below: \n")
            meta_data = dbx.files_get_metadata(top_folder)
            if not isinstance(meta_data, FolderMetadata):
                usr_input = input("Invalid folder. Try again? (y/n)")
                if "n" == usr_input:
                    sys.exit("No valid server folder was chosen. Exit now.")
                else:
                    if "y" == usr_input:
                        continue
                    print("Invalid response. Trying again.")
            return top_folder


def main():
    # server_cache_file_name = "server_files.pickle_" + str(datetime.now().date())
    local_top_folder = tkfd.askdirectory(title="choose the folder to store Dropbox backup")

    if not os.path.isdir(local_top_folder):
        sys.exit("No valid directory chosen. Exit.")

    print("Building local file cache...")
    local_cache = build_local_cache(local_top_folder)

    current_token = get_valid_token()
    if current_token == "":
        sys.exit("Invalid token provided. Exit.")

    print("Starting sync...")
    server_top_folder = get_valid_server_top_folder(current_token)

    print("Updating server file list...")
    server_cache = files_on_server(current_token, server_top_folder)

    print("Resolving differences...")
    download_list, remove_list, move_map = resolve_difference(server_cache, local_cache, local_top_folder)
    print("Resolved: %d to move, %d to remove, and %d to download." % (
        len(move_map), len(remove_list), len(download_list)))

    usr_input = input("Continue? (y/n) ")
    if usr_input == "y":

        move_files(move_map, local_cache, local_top_folder)

        remove_files(remove_list, local_cache, local_top_folder)

        download_files(current_token, download_list, local_top_folder)

        sys.exit("Backup finished.")

    else:
        sys.exit("Backup aborted.")


if __name__ == "__main__":
    main()
