#!/bin/sh

THUMBNAILER="totem-video-thumbnailer"
CONVERTER="convert"
MAX_ATTEMPTS=8

usage() {
    local code=${1:="0"}
    shift
    local msg="$*"
    if test "x$code" != "x0" -a "x$msg" != "x"; then
        echo
        echo "Error: $msg"
        echo
    fi 
    echo "Usage: $0 THUMBNAIL_SIZE VIDEO_FILE WORK_DIR [INPUT_DIR] [OUTPUT_DIR]"
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

THUMBNAIL_SIZE=$1
if test "x$THUMBNAIL_SIZE" = "x"; then
    usage 1 "No video size specified"
fi
VIDEO_FILE="$2"
if test "x$VIDEO_FILE" = "x"; then
    usage 1 "Video file not specified"
fi
WORK_DIR="$3"
if test "x$WORK_DIR" = "x"; then
    usage 1 "Working directory not specified"
fi
INPUT_DIR="${4:-$WORK_DIR}"
if test "x$INPUT_DIR" = "x"; then
    usage 1 "Input directory not specified"
fi
OUTPUT_DIR="${5:-$WORK_DIR}"
if test "x$OUTPUT_DIR" = "x"; then
    usage 1 "Output directory not specified"
fi

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
#THUMBNAIL_FILE=${VIDEO_FILE//.flv/}
THUMBNAIL_FILE=${VIDEO_FILE}
WORKING_PNG_THUMBNAIL="$WORK_DIR/$THUMBNAIL_FILE.png"
WORKING_JPG_THUMBNAIL="$WORK_DIR/$THUMBNAIL_FILE.jpg"
OUTPUT_JPG_THUMBNAIL="$OUTPUT_DIR/$THUMBNAIL_FILE.jpg"

if test ! -f "$INPUT_VIDEO"; then
    usage 1 "Video file '$INPUT_VIDEO' not found or invalid"
fi
if test ! -r "$INPUT_VIDEO"; then
    usage 1 "Video file '$INPUT_VIDEO' cannot be read (permission denied)"
fi

while /bin/true; do
    $THUMBNAILER --s "$THUMBNAIL_SIZE" "$INPUT_VIDEO" "$WORKING_PNG_THUMBNAIL" \
        || error $? "Failed to thumbnail video"
    if test ! -f "$WORKING_PNG_THUMBNAIL"; then
        MAX_ATTEMPTS=$((MAX_ATTEMPTS-1))
        test $MAX_ATTEMPTS = 0 && error 2 "Timeout, couldn't create thumbnail"
        sleep 5
        continue
    fi
    $CONVERTER "$WORKING_PNG_THUMBNAIL" "$WORKING_JPG_THUMBNAIL" \
        || usage $? "Failed to convert from PNG to JPG"
    rm "$WORKING_PNG_THUMBNAIL" \
        || usage $? "Failed to delete temporary PNG thumbnail"
    if test "$WORKING_JPG_THUMBNAIL" != "$OUTPUT_JPG_THUMBNAIL"; then
        mv "$WORKING_JPG_THUMBNAIL" "$OUTPUT_JPG_THUMBNAIL" \
            || error $? "Failed to move thumbnail to outgoing directory"
    fi
    break
done

exit 0
