# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.enums import VideoScaleMethodEnum

def _gcd(a,b):
    if b == 0:
        return a
    else:
        return _gcd(b,a%b)

def _reduce(f):
    num, denom = f
    divisor = _gcd(num, denom)
    if divisor > 1:
        return num / divisor, denom / divisor
    return f

def getVideoDAR(w, h, par):
    return _reduce((w * par[0], h * par[1]))

def getVideoSize(iw, ih, ipar,
                 ow=None, oh=None, opar=None,
                 mw=None, mh=None, method=VideoScaleMethodEnum.height):
    """
    Return the (Width, Height, PAR) of the output video.
    iw, ih and ipar should not be None, all other parameteres could be None.
        iw:    Input video width. Must be > 0.
        ih:    Input video height. Must be > 0.
        ipar:  Input video Pixel Aspect Ratio. Tuple of two integers > 0.
        ow:    Output video preferred width (Can be None)
        oh:    Output video preferred height (Can be None)
        opar:  Output video Pixel Aspect Ratio (Can be None)
        mw:    Maximum output video width (Can be None)
        mh:    Maximum output video height (Can be None)
        method: Preferred method for deducing video size when not specified;
            VideoScaleMethodEnum.width:     Preserve the original width
            VideoScaleMethodEnum.height:    Preserve the original height
            VideoScaleMethodEnum.downscale: Downscale one of the original axe
            VideoScaleMethodEnum.upscale:   Upscale one of the original axe

    The output PAR may be different from the preferred one if the
    size multiples are specified and do not respect the PAR (if wm/hm != opar).
    In this casse the output PAR is updated to match the changes.
    """
    # Convert to floats
    fiw = float(iw)
    fih = float(ih)
    fow = ow and float(ow)
    foh = oh and float(oh)

    # Reduce the PAR fraction to be able to use
    # the numerators and the denominators individually
    ipar = _reduce(ipar)
    if opar:
        par = _reduce(opar)
    else:
        par = ipar

    # Pixel ratio factor: InputPAR / OutputPAR
    parf = ipar[0] * par[1], ipar[1] * par[0]

    # If no size was specified chose one from input...
    if not (fow or foh):
        if (method == None) or (method == VideoScaleMethodEnum.height):
            #Preserve input height
            foh = fih
        elif method == VideoScaleMethodEnum.width:
            #Preserve input width
            fow = fiw
        elif method == VideoScaleMethodEnum.downscale:
            #Dfownscale the input
            if (fiw * parf[0]) > (fih * parf[1]):
                fow = fiw
            else:
                foh = fih
        elif method == VideoScaleMethodEnum.upscale:
            #Upscale the input
            if (fiw * parf[0]) >= (fih * parf[1]):
                foh = fih
            else:
                fow = fiw
        else:
            raise Exception("Unknfown preferred method '%s'" % method)

    fw, fh = None, None
    # Deduce output height from input size and preferred width
    if fow:
        fh = (fih * fow * parf[1]) / (fiw * parf[0])
    # Deduce output width from input size and preferred height
    if foh:
        fw = (fiw * foh * parf[0]) / (fih * parf[1])

    # If a size part is missing use the specified one
    if not fh:
        fh = foh
    if not fw:
        fw = fow

    # If output preferred width and height were both specified,
    # force the one that make the output size smaller
    # or equal to the preferred output size
    if fow and foh:
        if fw < fow:
            fh = foh
        elif fh < foh:
            fw = fow

    # Scale the output size if too big
    if mw and fw > mw:
        fh = (fh * mw) / fw
        fw = mw
    if mh and fh > mh:
        fw = (fw * mh) / fh
        fh = mh

    rw = int(round(fw))
    rh = int(round(fh))

    return rw, rh, par
