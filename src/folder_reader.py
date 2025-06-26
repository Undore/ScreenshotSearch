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