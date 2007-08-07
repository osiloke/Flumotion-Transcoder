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
                 mw=None, mh=None, wm=None, hm=None,
                 method=VideoScaleMethodEnum.height):
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
        wm:    Width multiple (Can be None)
        hm:    Height multiple (Can be None)
        method: Preferred method for deducing video size when not specified;
            VideoScaleMethodEnum.width:     Preserve the original width
            VideoScaleMethodEnum.height:    Preserve the original height
            VideoScaleMethodEnum.downscale: Downscale one of the original axe
            VideoScaleMethodEnum.upscale:   Upscale one of the original axe
    """
    #Convert to floats
    iw = float(iw)
    ih = float(ih)
    ow = ow and float(ow)
    oh = oh and float(oh)
    
    #Reduce the PAR fraction to be able to use 
    #the numerators and the denominators individually
    ipar = _reduce(ipar)
    if opar:
        par = _reduce(opar)
    else:
        par = ipar
        
    #Pixel ratio factor: InputPAR / OutputPAR
    parf = ipar[0] * par[1], ipar[1] * par[0]

    #If no size was specified chose one from input...
    if not (ow or oh):
        if (method == None) or (method == VideoScaleMethodEnum.height):
            #Preserve input height
            oh = ih
        elif method == VideoScaleMethodEnum.width:
            #Preserve input width
            ow = iw
        elif method == VideoScaleMethodEnum.downscale:
            #Downscale the input
            if (iw * parf[0]) > (ih * parf[1]):
                ow = iw
            else:
                oh = ih
        elif method == VideoScaleMethodEnum.upscale:
            #Upscale the input
            if (iw * parf[0]) >= (ih * parf[1]):
                oh = ih
            else:
                ow = iw
        else:
            raise Exception("Unknown preferred method '%s'" % method)

    w, h = None, None
    #Deduce output height from input size and preferred width
    if ow:
        h = (ih * ow * parf[1]) / (iw * parf[0])        
    #Deduce output width from input size and preferred height
    if oh:
        w = (iw * oh * parf[0]) / (ih * parf[1])

    #If a size part is missing use the specified one
    if not h:
        h = oh
    if not w:
        w = ow
    
    #If output preferred width and height were both specified,
    #force the one that make the output size smaller
    #or equal to the preferred output size
    if ow and oh:
        if w < ow:
            h = oh
        elif h < oh:
            w = ow

    #Scale the output size if too big
    if mw and w > mw:
        h = (h * mw) / w
        w = mw
    if mh and h > mh:
        w = (w * mh) / h
        h = mh
    
    return int(round(w)), int(round(h)), par
