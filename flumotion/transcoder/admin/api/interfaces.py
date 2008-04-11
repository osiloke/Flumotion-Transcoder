# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.inhouse.spread import mediums 


class IMedium(mediums.IServerMedium):
    pass


class ITranscoderGateway(IMedium):
    
    def getWorkerSet(self):
        pass

    def getStore(self):
        pass
    
    def getScheduler(self):
        pass


class IWorkerSetMedium(IMedium):

    def getWorkers(self):
        pass
    
    def getWorker(self, identifier):
        pass


class IStoreMedium(IMedium):
    
    def getDefaults(self):
        pass
    
    def getCustomers(self):
        pass
    
    def getCustomer(self, identifier):
        pass
    

class ISchedulerMedium(IMedium):
    pass


class INamedMedium(IMedium):

    def getIdentifier(self):
        pass
    
    def getName(self):
        pass
    
    def getLabel(self):
        pass


class IWorkerMedium(INamedMedium):

    def getHost(self):
        pass


class ICustomerMedium(INamedMedium):
    
    def getProfiles(self):
        pass
    
    def getProfile(self, identifier):
        pass

    
class IProfileMedium(INamedMedium):
    
    def getTargets(self):
        pass
    
    def getTarget(self, identifier):
        pass


class ITargetMedium(INamedMedium):
    
    def getConfig(self):
        pass


class IConfigMedium(IMedium):
    pass


class IIdentityConfigMedium(IConfigMedium):
    pass


class IAudioConfigMedium(IConfigMedium):
    pass


class IVideoConfigMedium(IConfigMedium):
    pass


class IAudioVideoConfigMedium(IAudioConfigMedium, IVideoConfigMedium):
    pass


class IThumbnailsConfigMedium(IConfigMedium):
    pass
