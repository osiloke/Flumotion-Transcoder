# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.


from zope.interface import Interface

from flumotion.transcoder.errors import TranscoderError


class DataSourceError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)

class InitializationError(DataSourceError):
    def __init__(self, *args, **kwargs):
        DataSourceError.__init__(self, *args, **kwargs)

class StoringError(DataSourceError):
    def __init__(self, *args, **kwargs):
        DataSourceError.__init__(self, *args, **kwargs)

class RetrievalError(DataSourceError):
    def __init__(self, *args, **kwargs):
        DataSourceError.__init__(self, *args, **kwargs)

class DataNotFoundError(RetrievalError):
    def __init__(self, *args, **kwargs):
        RetrievalError.__init__(self, *args, **kwargs)

class ReadOnlyDataError(StoringError):
    def __init__(self, *args, **kwargs):
        StoringError.__init__(self, *args, **kwargs)

class DuplicatedDataError(StoringError):
    def __init__(self, *args, **kwargs):
        StoringError.__init__(self, *args, **kwargs)

class DataDependencyError(StoringError):
    def __init__(self, *args, **kwargs):
        StoringError.__init__(self, *args, **kwargs)


class IDataSource(Interface):
    """
    The data source allow the retrieval, creation, insertion and deletion
    of "container" objects in an abstract source.
    The given container are unspecified, apart for there fields
    and the equality operator.
    The equality operator compare if the objects represent the same
    element in the source, not that they have the same field values.
    Two new element that has not been stored in the source are never equal.
    If an element is retrieved and modified more than one time before
    storing them, all modification but the last stored one are lost
    without warning. THERE IS NO CONCURENT MODIFICATION PROTECTION.
    """

    def initialize(self):
        """
        Return a deferred.
        Initialize the data source.
        """

    def waitReady(self):
        """
        Returns a deferred that is called when the source
        is ready to provide data, or if the source fail
        to initialize
        """

    def retrieveDefaults(self):
        """
        Returns a deferred.
        The result on success is a "container" object 
        with the following fields:
            outputMediaTemplate (str)
            outputThumbTemplate (str)
            linkFileTemplate (str)
            configFileTemplate (str)
            reportFileTemplate (str)
            monitoringPeriod (int) : 
                Gives the default period used to monitor the filesystem.
            transcodingTimeout (int) :
                Gives the default timeout of the transcoding jobs.
            postprocessTimeout (int) :
                Gives the default timeout of the post-processing.
            preprocessTimeout (int) :
                Gives the default timeout of the pre-processing.
            mailSubjectTemplate (str) :
                Gives the default template for the mail notifications subject.
            mailBodyTemplate (str) :
                Gives the default template for the mail notifications body.
            GETRequestTimeout (int) :
                Gives the default timeout for GET request notifications.
            GETRequestRetryCount (int) :
                Gives the default retry count for GET request notifications.
            GETRequestRetrySleep (int) :
                Gives the default time between retry 
                for GET request notifications.
        """
        
    def retrieveCustomers(self):
        """
        Returns a deferred.
        The result on success is a list of "container" objects
        with the following fields:
           name (str) : The customer name used by the transcoder.
           subdir (str) can be None : The sub-directory where the transcoder
               root is. If not specified, it will be deduced from the customer name.
         Overriding fields:
           inputDir (str) can be None
           outputDir (str) can be None
           failedDir (str) can be None
           doneDir (str) can be None
           linkDir (str) can be None
           workDir (str) can be None
           configDir (str) can be None
           failedRepDir (str) can be None
           doneRepDir (str) can be None
           outputMediaTemplate (str)
           outputThumbTemplate (str)
           linkFileTemplate (str)
           configFileTemplate (str)
           reportFileTemplate (str)
           linkTemplate (str) can be None
           linkURLPrefix (str) can be None
           enablePostprocessing (bool) can be None
           enablePreprocessing (bool) can be None
           enableLinkFiles (bool) can be None
           transcodingPriority (int) can be None
           processPriority (int) can be None
           preprocessCommand (str) can be None
           postprocessCommand (str) can be None
           preprocesstimeout (int) can be None
           postprocessTimeout (int) can be None
           transcodingTimeout (int) can be None
           monitoringPeriod (int) can be None
        """
        
    def retrieveCustomerInfo(self, customerData):
        """
        Returns a deferred.
        The result on success is a "container" objects
        with the following READ ONLY fields:
            name (str) can be None
            contact (str) can be None
            addresses (str[]) maximum size of 3, can be empty
            phone (str) can be None
            email (str) can be None
        """
        
    def retrieveProfiles(self, customerData):
        """
        Returns a deferred.
        The result on success is a list of "container" objects
        with the following fields:
           name (str)
           subdir (str)  can be None
         Overriding fields:
           inputDir (str) can be None
           outputDir (str) can be None
           failedDir (str) can be None
           doneDir (str) can be None
           linkDir (str) can be None
           workDir (str) can be None
           configDir (str) can be None
           failedRepDir (str) can be None
           doneRepDir (str) can be None
           outputMediaTemplate (str) can be None
           outputThumbTemplate (str) can be None
           linkFileTemplate (str) can be None
           configFileTemplate (str) can be None
           reportFileTemplate (str) can be None
           linkTemplate (str) can be None
           linkURLPrefix (str) can be None
           enablePostprocessing (bool) can be None
           enablePreprocessing (bool) can be None
           enableLinkFiles (bool) can be None
           transcodingPriority (int) can be None
           processPriority (int) can be None
           preprocessCommand (str) can be None
           postprocessCommand (str) can be None
           preprocesstimeout (int) can be None
           postprocessTimeout (int) can be None
           transcodingTimeout (int) can be None
           monitoringPeriod (int) can be None
        """
        
    def retrieveNotifications(self, withGlobal, customerData, 
                              profileData, targetData):
        """
        Returns a deferred.
        The returned list contains all the notification 
        that apply to the specified parameteres:
            if withGlobal is True, the result contains
                the global notifications.
            if customerData is not None, the result contains
                the customer specific notifications.
            if profileData is not None, the result contains
                the profile specific notifications.
            if targetData is not None, the result contains
                the target specific notifications.
        In any cases, the specified data must be related,
        in other words, if a profile and a customer are specified
        the profile must be of the customer.
        The result on success is a list of "container" objects
        with the following fields depending on the notification type:
            For all:
                type (enum of ['email', 'get']
                triggers (set) with element in enum ['done', 'failed']
            For type == 'email':
                subjectTemplate (str) can be None
                bodyTemplate (str) can be None
                attachments (set) with element in enum ['report']
                addresses dict with keys enum ('to', cc', bcc')
                    of list of tuple with (name, email)
            For type == 'get':
                requestTemplate (str)
                timeout (int) can be None
                retryCount (int) can be None
                retrySleep (int) can be None
        """
        
    def retrieveTargets(self, profileData):
        """
        Returns a deferred.
        The result on success is a list of "container" objects
        with the following fields:
           name (str)
           extension (str)
           subdir (str) can be None
         Overriding fields:
           linkTemplate (str) can be None
           linkURLPrefix (str) can be None
           outputFileTemplate (str) can be None
           linkFileTemplate (str) can be None
           enablePostprocessing (bool) can be None
           enableLinkFiles (bool) can be None
           postprocessCommand (str) can be None
           postprocessTimeout (int) can be None
        """
       
    def retrieveTargetConfig(self, targetData):
        """
        Returns a deferred.
        The result on success is a "container" objects
        that depend of the target type.
        For all:
            type (TargetTypeEnum)
        For an Audio and Audio/Video targets, it has the following fields:
            muxer (str)
            audioEncoder (str)
            audioRate (str) 
            audioChannels (str)
        For a video and Audio/Video targets, it has the following fields:
            muxer (str)
            videoEncoder (str)
            videoWidth (int)
            videoHeight (int)
            videoMaxWidth (int)
            videoMaxHeight (int)
            videoPAR (int[2])
            videoFramerate (int[2])
            videoScaleMethod (VideoScaleMethodEnum)
        For Audio/Video targets, it has the following additional fields:
            tolerance (AudioVideoToleranceEnum)
        For a Thumbnails targets, it has the following fields:
            thumbsWidth (int)
            thumbsHeight (int)
            periodValue (int)
            periodUnit (PeriodUnitEnum)
            maxCount (int)
            format (ThumbOutputTypeEnum)
        """

    def newCustomer(self, cusomerId):
        """
        Creates a new customer container.
        It's not added to the store, it should be
        filled and then the store method should be call.
        """

    def newProfile(self, customerData):
        """
        Creates a new profile container for the specified customer.
        It's not added to the store, it should be
        filled and then the store method should be call.
        """
    
    def newNotification(self, type, data):
        """
        Creates a new notification container 
        of the specified type in ('email', 'get').
        The specified data must be customer data, 
        profile data, target data or None.
            None: apply to all customers transcoding
            Customer data: apply to all profiles transcoding
                of the specified customer
            Profile data: apply to a specific customer's
                profile transcoding
            Target data: apply to a specific target of a profile
        It's not added to the store, it should be
        filled and then the store method should be call.
        """
    
    def newTarget(self, profileData):
        """
        Creates a new target container object.
        """

    def newTargetConfig(self, targetData):
        """
        Creates a new target config container object.
        """
        
    def newReport(self, profileData):
        """
        Creates a new report container object.
        """
        
    def newTargetReport(self, reportData):
        """
        Creates a new target report container object.
        """
        
    def newNotificationReport(self, reportData, notificationData):
        """
        Creates a new notification report container object.
        """
        
    def store(self, *data):
        """
        Returns a deferred.
        Store all the specified container objectes.
        The objects must have been created by the store.
        All the objecte are stored atomically if the
        store support it.
        """
    
    def delete(self, *data):
        """
        Return a deferred.
        Delete all the specified container objectes.
        The objects must have been created by the store.
        All the objecte are deleted atomically if the
        store support it.
        """
