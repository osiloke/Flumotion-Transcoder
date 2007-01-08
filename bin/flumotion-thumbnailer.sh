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
    echo "Usage: $0 VIDEO_FILE WORKING_DIRECTORY [OUTGOING_DIRECTORY]"
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

VIDEO_FILE="$1"
if test "x$VIDEO_FILE" = "x"; then
    usage 1 "Video file not specified"
fi
WORKING_DIRECTORY="$2"
if test "x$WORKING_DIRECTORY" = "x"; then
    usage 1 "Working directory not specified"
fi
OUTGOING_DIRECTORY="${3:-$WORKING_DIRECTORY}"
if test "x$OUTGOING_DIRECTORY" = "x"; then
    usage 1 "Outgoing directory not specified"
fi

if test ! -d "$WORKING_DIRECTORY"; then
    usage 1 "Working directory '$WORKING_DIRECTORY' not found"
fi
if test ! -w "$WORKING_DIRECTORY"; then
    usage 1 "Working directory '$WORKING_DIRECTORY' cannot be written (permision denied)"
fi

if test ! -d "$OUTGOING_DIRECTORY"; then
    usage 1 "Outgoing directory '$OUTGOING_DIRECTORY' not found"
fi
if test ! -w "$OUTGOING_DIRECTORY"; then
    usage 1 "Outgoing directory '$OUTGOING_DIRECTORY' cannot be written (permision denied)"
fi

WORKING_VIDEO="$WORKING_DIRECTORY/$VIDEO_FILE"
WORKING_PNG_THUMBNAIL="$WORKING_DIRECTORY/$VIDEO_FILE.png"
WORKING_JPG_THUMBNAIL="$WORKING_DIRECTORY/$VIDEO_FILE.jpg"
OUTGOING_JPG_THUMBNAIL="$OUTGOING_DIRECTORY/$VIDEO_FILE.jpg"

if test ! -f "$WORKING_VIDEO"; then
    usage 1 "Video file '$WORKING_VIDEO' not found or invalid"
fi
if test ! -r "$WORKING_VIDEO"; then
    usage 1 "Video file '$WORKING_VIDEO' cannot be read (permission denied)"
fi

while /bin/true; do
    $THUMBNAILER "$WORKING_VIDEO" "$WORKING_PNG_THUMBNAIL" \
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
    if test "$WORKING_JPG_THUMBNAIL" != "$OUTGOING_JPG_THUMBNAIL"; then
        mv "$WORKING_JPG_THUMBNAIL" "$OUTGOING_JPG_THUMBNAIL" \
            || error $? "Failed to move thumbnail to outgoing directory"
    fi
    break
done

exit 0
