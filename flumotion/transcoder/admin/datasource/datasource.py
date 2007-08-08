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

class DeletionError(DataSourceError):
    def __init__(self, *args, **kwargs):
        DataSourceError.__init__(self, *args, **kwargs)

class ResetError(DataSourceError):
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
    The given container are unspecified, apart for there fields,
    the equality operator, and an identifier fields that uniquely
    and persistently identify a "record" and that is None when not stored.
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

    def waitReady(self, timeout=None):
        """
        Returns a deferred that is called when the source
        is ready to provide data, if the source fail to initialize
        or if the specified timeout is reached.
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
            transcodingPriority (int) :
                Gives the default priority of the transcoding jobs.
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
            mailTimeout (int) :
                Gives the default timeout for mail notifications.
            mailRetryCount (int) :
                Gives the default retry count for mail notifications.
            mailRetrySleep (int) :
                Gives the default time between retry for mail notifications.                
            HTTPRequestTimeout (int) :
                Gives the default timeout for HTTP request notifications.
            HTTPRequestRetryCount (int) :
                Gives the default retry count for HTTP request notifications.
            HTTPRequestRetrySleep (int) :
                Gives the default time between retry 
                for HTTP request notifications.
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
           customerPriority (int) can be None
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
           outputDir (str) can be None
           linkDir (str) can be None
           workDir (str) can be None
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
            videoWidthMultiple (int)
            videoHeightMultiple (int)
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
        
    def retrieveGlobalNotifications(self):
        """
        Returns a deferred.
        The returned list contains all global notifications.
        The result on success is a list of "container" objects
        with the following fields depending on the notification type:
            For all:
                type (NotificationTypeEnum)
                triggers (set of NotificationTriggerEnum)
                timeout (int) can be None
                retryMax (int) can be None
                retrySleep (int) can be None
            For type == NotificationTypeEnum.email:
                subjectTemplate (str) can be None
                bodyTemplate (str) can be None
                attachments (set of DocumentTypeEnum)
                recipients dict with MailAddressTypeEnum as keys
                    of list of tuple with (name, email)
                    where name can be None
            For type == NotificationTypeEnum.get_request:
                requestTemplate (str)
        """
        
    def retrieveCustomerNotifications(self, customerData):
        """
        Returns a deferred.
        The returned list contains all customers' notifications.
        See retrieveGlobalNotifications for result specifications.
        """

    def retrieveProfileNotifications(self, profileData):
        """
        Returns a deferred.
        The returned list contains all profiles' notifications.
        See retrieveGlobalNotifications for result specifications.
        """

    def retrieveTargetNotifications(self, targetData):
        """
        Returns a deferred.
        The returned list contains all targets' notifications.
        See retrieveGlobalNotifications for result specifications.
        """
        
    def retrieveActivities(self, type, states=None):
        """
        Returns a deferred.
        The result on success is a list of the activities
        with the specified type and state in the specified 
        list states (if not None or empty)
        as "container" objects with the following fields:
           type (ActivityTypeEnum)
           subtype (TranscodingTypeEnum or NotificationTypeEnum)
           state (ActivityStateEnum)
           startTime (datetime)
           lastTime (dateTime)
           customerName (str)
           profileName (str)
           targetName (str)
        For type == transcoding, reference is a data container:
           inputRelPath (str)
        For type == notification:
           trigger (NotificationTriggerEnum)
           timeout (int)
           retryCount (int)
           retryMax (int)
           retrySleep (int)
           data (dict)
        """

    def newActivity(self, type, subtype):
        """
        Creates a new activity container of a specified type and subtype.
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
        of the specified type (NotificationTypeEnum).
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
    
    def reset(self, *data):
        """
        Returns a deferred.
        Reset the values of the specified container objects
        to there original value from the data source.
        If a specified container was never stored,
        its values are not changed.
        """
    
    def delete(self, *data):
        """
        Return a deferred.
        Delete all the specified container objectes.
        The objects must have been created by the store.
        All the objecte are deleted atomically if the
        store support it.
        Deletion is not an operation that could be
        reversed by calling reset.
        """
