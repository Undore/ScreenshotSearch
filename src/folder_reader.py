import os


class FolderReader:
    @staticmethod
    def walk_files(path: str):
        found_files = []
        for root, _, files in os.walk(path):
            for file in files:
                abs_path = os.path.abspath(os.path.join(root, file))
                found_files.append(abs_path)

        return found_files

    @staticmethod
    def convert_path(search_folder_prefix: str, old_path) -> str | None:
        """
        Convert path to current folder scope
        :param search_folder_prefix: Folder prefix to search. For example, samples or video (folder)
        :param old_path: Another scope folder path
        :return: Normal path if found
        """
        old_path_parts = old_path.split('/')
        last_part_index = 0
        for indx, part in enumerate(old_path_parts):
            last_part_index = indx
            if part == search_folder_prefix:
                break
        else:
            return None

        return "/".join(old_path_parts[last_part_index:])
