# Screenshot Search by Undore

This script provides tools to search for certain images in videos

As input, script takes **originals** and **comparing** files

Originals are images, which should be found in comparing files (which are videos)

First of all, `settings.py`:
```
`ORIGINALS_FOLDER_NAME` - name of the folder in current directory root, which contains originals

`COMPARING_FOLDER_NAME` - name of the folder in current directory root, which contains videos

`LOGGING` - Recommended to keep default

`BUFFER_IMAGES` - If enabled, will store frames in a temp directory, which can be faster on slow processors, but fast SSDs. 
**It is highly recommended to NOT use this, if you have a normal or good CPU** (it can make the process just slower and takes a hell lot of space)

If Buffering is off, every cycle is going to read frames from videos and ignore cache

`CLEAR_TEMP` - Clear buffered frames on start. If disabled, system can pick up frames, cached on previous starts

`PROTOCOLS` - Currently there are 3 protocols supported:

## SSIM and PHASH
Comparing full image using corresponding protocol

## TEMPLATE
Expects original image to be a **part** of a **frame**. This is useful if you don`t have the **whole** image, but only have a part of it.
Other protocols won't help in this case, so use template search.

`protocol similarity` - This setting sets threshold (in percentage 0 - 100 %), which will be classified as matching frame.
Basically, the higher it is, the more similar images must be for them to be included in search results

`BASE_PATH` - Highly recommended to not change this
```

When files are ready (By the way, file names must be unique, even in nested folders), to start the search, just start `main.py`

Progress slider will appear.

# How does this work?

System cycles through every single original file and for every file it iterates all frames of all present videos.

This means, that if you have 10 images and 10 videos, each video containing (for example) 100 frames, system will do **10\*10\*100** = **10 000** frame comparisons

This will take a while, so it`s better to use just one algorythm and run this on some kind of server.

# After results are ready

Results will be exported to results.json

After export, you can use `resolve_results.py` to calculate scores of results and convert paths, if rendering was performed on a server.
System will automatically convert paths for your system.

`Hint`
Don`t forget to set RESULTS_FILENAME variable to corresponding filename

When you have resolved results with scores, you can run `remove_duplicate_results.py`, which will remove duplicate frames.

### Duplicate frames
Frame can be considered duplicate if it is literally duplicated in results, or if there is already timestamp nearby.

For example, if `TIME_THRESHOLD_MS = 500`, two frames on `0:01:05.5` and `0:01:05.6` will be converted into just `0:01:05.5`


# Making a result hierarchy

You can unpack all your parsed and cleaned results into folder tree.

Folder tree will look like this:
```
PROGRAM ROOT /
----main.py

----dist/
--------0.499999 <--- score.  The higher the more simmilar is the frame
------------original_file_name_this_is_a_folder1.png
----------------video_in_which_original_was_found_this_is_a_folder.mp4
--------------------0-01-57.jpg  <--- This is a frame image, named as a timecode from video

----make_result_hierarchy.py

```

# Waring!
This will take a **lot** of space on disk.

`So, Before doing this`
run `calc_size.py` to calculate approx disk space requirements

# That's basically it!
This is my personal project, and it's probably not perfect, but  