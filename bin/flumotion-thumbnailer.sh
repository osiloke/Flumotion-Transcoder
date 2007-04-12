#!/bin/sh

THUMBNAILER="totem-video-thumbnailer"
CONVERTER="convert"
CONVERTER_PARAMS=""
MAX_ATTEMPTS=8

#DEFAULT VALUES
DEFAULT_THUMBNAIL_SIZE="320x240"
DEFAULT_FORMAT_EXT="jpg"
DEFAULT_REMOVE_EXT="0"

usage() {
    local code=${1:="0"}
    shift
    local msg="$*"
    if test "x$code" != "x0" -a "x$msg" != "x"; then
        echo
        echo "Error: $msg"
        echo
    fi 
    echo "Usage: $0 [OPTIONS] WORK_DIR VIDEO_FILE"
    echo "Options:"
    echo "   -s THUMBNAIL_SIZE: Size wanted thumbnail size, no guarentee. Default: $DEFAULT_THUMBNAIL_SIZE."
    echo "   -x FORMAT_EXT: The thumbnail format extension to use. Default: $DEFAULT_FORMAT_EXT"
    echo "   -c CONVERT_PARAMS: Additional convert filters like '-resize 160' to force the thumbnail width"
    echo "   -i INPUT_DIR: the directory where the video to thumbnail is."
    echo "   -o OUTPUT_DIR: the directory where the thumbnail should go."
    echo "   -r: If the original video extension should be removed"
    echo "   -h: show this usage information"
    echo
    exit $code
}

error() {
    local code=${1:="0"}
    shift
    local msg="$*"
    if test "x$code" != "x0" -a "x$msg" != "x"; then
        echo "Error: $msg"
    fi 
    exit $code
}


while getopts "hrs:c:x:i:o:" o; do
    case $o in
    h)  usage 0;;
    r)  REMOVE_EXT=1;;
    s)  THUMBNAIL_SIZE="$OPTARG";;
    c)  CONVERTER_PARAMS="$CONVERTER_PARAMS $OPTARG";;
    x)  FORMAT_EXT="$OPTARG";;
    i)  INPUT_DIR="$OPTARG";;
    o)  OUTPUT_DIR="$OPTARG";;
    *)  usage 2 "Unkonw option '$o'";;
    esac
done
shift $(($OPTIND - 1))

WORK_DIR="$1"
if test "x$WORK_DIR" = "x"; then
    usage 1 "Working directory not specified"
fi

VIDEO_FILE="$2"
if test "x$VIDEO_FILE" = "x"; then
    usage 1 "Video file not specified"
fi


REMOVE_EXT=${REMOVE_EXT:-$DEFAULT_REMOVE_EXT}
THUMBNAIL_SIZE=${THUMBNAIL_SIZE:-$DEFAULT_THUMBNAIL_SIZE}
FORMAT_EXT=${FORMAT_EXT:-$DEFAULT_FORMAT_EXT}
INPUT_DIR="${INPUT_DIR:-$WORK_DIR}"
OUTPUT_DIR="${OUTPUT_DIR:-$WORK_DIR}"

if test ! -d "$WORK_DIR"; then
    usage 1 "Working directory '$WORK_DIR' not found"
fi
if test ! -w "$WORK_DIR"; then
    usage 1 "Working directory '$WORK_DIR' cannot be written (permision denied)"
fi

if test ! -d "$INPUT_DIR"; then
    usage 1 "Input directory '$INPUT_DIR' not found"
fi
if test ! -r "$INPUT_DIR"; then
    usage 1 "Input directory '$INPUT_DIR' cannot be read (permision denied)"
fi

if test ! -d "$OUTPUT_DIR"; then
    usage 1 "Output directory '$OUTPUT_DIR' not found"
fi
if test ! -w "$OUTPUT_DIR"; then
    usage 1 "Output directory '$OUTPUT_DIR' cannot be written (permision denied)"
fi

INPUT_VIDEO="$INPUT_DIR/$VIDEO_FILE"
if test "x$REMOVE_EXT" = "x1"; then
    THUMBNAIL_FILE=$(echo $VIDEO_FILE | sed "s/\(.*\)\.[^\.]*/\1/")
else
    THUMBNAIL_FILE=${VIDEO_FILE}
fi
WORKING_PNG_THUMBNAIL="$WORK_DIR/$THUMBNAIL_FILE.png"
WORKING_OUT_THUMBNAIL="$WORK_DIR/$THUMBNAIL_FILE.$FORMAT_EXT"
OUTPUT_OUT_THUMBNAIL="$OUTPUT_DIR/$THUMBNAIL_FILE.$FORMAT_EXT"

if test ! -f "$INPUT_VIDEO"; then
    usage 1 "Video file '$INPUT_VIDEO' not found or invalid"
fi
if test ! -r "$INPUT_VIDEO"; then
    usage 1 "Video file '$INPUT_VIDEO' cannot be read (permission denied)"
fi

while /bin/true; do
    $THUMBNAILER -s "$THUMBNAIL_SIZE" "$INPUT_VIDEO" "$WORKING_PNG_THUMBNAIL" \
        || error $? "Failed to thumbnail video"
    if test ! -f "$WORKING_PNG_THUMBNAIL"; then
        MAX_ATTEMPTS=$((MAX_ATTEMPTS-1))
        test $MAX_ATTEMPTS = 0 && error 2 "Timeout, couldn't create thumbnail"
        sleep 5
        continue
    fi
    set -x
    $CONVERTER "$WORKING_PNG_THUMBNAIL" $CONVERTER_PARAMS "$WORKING_OUT_THUMBNAIL" \
        || usage $? "Failed to convert from PNG to JPG"
    rm "$WORKING_PNG_THUMBNAIL" \
        || usage $? "Failed to delete temporary PNG thumbnail"
    if test "$WORKING_OUT_THUMBNAIL" != "$OUTPUT_OUT_THUMBNAIL"; then
        mv "$WORKING_OUT_THUMBNAIL" "$OUTPUT_OUT_THUMBNAIL" \
            || error $? "Failed to move thumbnail to outgoing directory"
    fi
    break
done

exit 0
