--  The whole schema for the transcoder database VERSION 20081230

-- schema_information must be updated and looked at before committing schema changes
-- schema_version is YYYYMMDDXX where XX is 00 for the first schema change on
-- particular day, extra changes same day should increment the XX
create table if not exists schema_information (
        schema_version int(9) not null,
        upgrading_soon boolean default false,
        upgrading_currently boolean default false
) engine=InnoDB;

insert into schema_information(schema_version, upgrading_soon, upgrading_currently)
values ('2008123000', false, false);



-- a lookup table of possible transcode outcomes
create table if not exists transcoder_failures (
        failure_id int primary key,
        failure_name varchar(100)
) engine=InnoDB;

-- REMEMBER to keep in sync with flumotion.transcoder.enums.transcodingOutcomeEnum
insert into transcoder_failures values
        (1, 'Wrong mime type'),
        (2, 'Wrong file type'),
        (3, 'Video file too small'),
        (4, 'Audio file too small'),
        (5, 'Corrupted');



-- the main table that holds transcoding reports
create table if not exists transcoder_reports (
        transcoder_report_id int primary key auto_increment,
        customer_id varchar(100) not null,
        profile_id varchar(100) not null,
        relative_path varchar(100) not null,
        report_path varchar(100),
        file_checksum char(32), -- not null
        file_size int,
        file_type varchar(100),
        mime_type varchar(100),
        audio_codec varchar(100),
        video_codec varchar(100),
        creation_time datetime,
        modification_time datetime,
        detection_time datetime,
        queueing_time datetime,
        transcoding_start_time datetime,
        transcoding_finish_time datetime,
        total_cpu_time float,
        total_real_time float,
        attempt_count int,
        machine_name varchar(100),
        worker_name varchar(100),
        failure_id int,
        outcome boolean not null,
        successful boolean not null,
        invalid_output boolean default 0,

        comment varchar(1000),

        foreign key(failure_id) references transcoder_failures(failure_id),
        -- if a file has failed, but the end result is a success there
        -- should be a comment saying how we managed to finally
        -- transcode the file (innodb ignores this, though...)
        check (outcome or (not successful) or (comment is not null))
) engine=InnoDB;


-- Various helpful views follow, encompassing some QoS metrics that we keep track of

create or replace view transcoder_reports_with_failures as
        select * from transcoder_reports natural join transcoder_failures;

create or replace view transcoded_manually as
select
        customer_id,
        profile_id,
        relative_path,
        failure_name,
        comment
from
        transcoder_reports
        natural left join transcoder_failures
where
        (not outcome or invalid_output) and successful;

create or replace view transcoder_outcomes_per_customer as
select
        customer_id,
        sum(case when (outcome and not invalid_output) then 1 else 0 end) as successful_transcods,
        sum(case when (not outcome or invalid_output) then 1 else 0 end) as failed_transcods,
        sum(case when (not outcome or invalid_output) and (failure_id is null) then 1 else 0 end) as failed_unexpectedly_transcods
from
        transcoder_reports
group by customer_id;

create or replace view transcoder_outcomes_per_profile as
select
        customer_id,
        profile_id,
        sum(case when (outcome and not invalid_output) then 1 else 0 end) as successful_transcods,
        sum(case when (not outcome or invalid_output) then 1 else 0 end) as failed_transcods,
        sum(case when (not outcome or invalid_output) and (failure_id is null) then 1 else 0 end) as failed_unexpectedly_transcods
from
        transcoder_reports
group by customer_id, profile_id;

create or replace view transcoder_results_per_customer as
select
        customer_id,
        sum(case when successful then 1 else 0 end) as successful_transcods,
        sum(case when successful then 0 else 1 end) as failed_transcods
from
        transcoder_reports
group by customer_id;

create or replace view transcoder_results_per_profile as
select
        customer_id,
        profile_id,
        sum(case when successful then 1 else 0 end) as successful_transcods,
        sum(case when successful then 0 else 1 end) as failed_transcods
from
        transcoder_reports
group by customer_id, profile_id;

-- internal success rate per customer rounded to 3 decimal numbers
create or replace view internal_success_rate_per_customer as
select
        customer_id,
        successful_transcods + failed_transcods as number_of_transcods,
        round(successful_transcods / (successful_transcods + failed_unexpectedly_transcods), 3) * 100 as success_rate
from transcoder_outcomes_per_customer;

-- internal success rate per customer and profile rounded to 3 decimal numbers
create or replace view internal_success_rate_per_profile as
select
        customer_id,
        profile_id,
        successful_transcods + failed_transcods as number_of_transcods,
        round(successful_transcods / (successful_transcods + failed_unexpectedly_transcods), 3) * 100 as success_rate
from transcoder_outcomes_per_profile;

-- external success rate per customer rounded to 3 decimal numbers
create or replace view external_success_rate_per_customer as
select
        customer_id,
        successful_transcods + failed_transcods as number_of_transcods,
        round(successful_transcods / (successful_transcods + failed_transcods), 3) * 100 as success_rate
from transcoder_results_per_customer;

-- total time spent by files in various phases
create or replace view average_time_spent_in_phases as
select
        avg(timestampdiff(SECOND, detection_time, queueing_time)) as waiting_for_queuing,
        avg(timestampdiff(SECOND, queueing_time, transcoding_start_time)) as in_queue,
        avg(timestampdiff(SECOND, transcoding_start_time, transcoding_finish_time)) as transcoding,
        avg(timestampdiff(SECOND, detection_time, transcoding_finish_time)) as total
from transcoder_reports;

-- time spent in various phases per customer
create or replace view average_time_spent_in_phases_per_customer as
select
        customer_id,
        avg(timestampdiff(SECOND, detection_time, queueing_time)) as waiting_for_queuing,
        avg(timestampdiff(SECOND, queueing_time, transcoding_start_time)) as in_queue,
        avg(timestampdiff(SECOND, transcoding_start_time, transcoding_finish_time)) as transcoding,
        avg(timestampdiff(SECOND, detection_time, transcoding_finish_time)) as total
from transcoder_reports
group by customer_id;

-- time spent in various phases per customer and profile
create or replace view average_time_spent_in_phases_per_profile as
select
        customer_id,
        profile_id,
        avg(timestampdiff(SECOND, detection_time, queueing_time)) as waiting_for_queuing,
        avg(timestampdiff(SECOND, queueing_time, transcoding_start_time)) as in_queue,
        avg(timestampdiff(SECOND, transcoding_start_time, transcoding_finish_time)) as transcoding,
        avg(timestampdiff(SECOND, detection_time, transcoding_finish_time)) as total
from transcoder_reports
group by customer_id, profile_id;

-- reports taking into account only unique files

create or replace view unique_transcoder_reports as
select
        customer_id,
        profile_id,
        case when count(transcoder_report_id) = 1 then max(relative_path) else null end as relative_path, -- no sense when groupped, but avoid NULL when there's only one thing in the group
        case when count(transcoder_report_id) = 1 then max(report_path) else null end as report_path,
        file_checksum,
        max(file_size),
        max(file_type),
        max(mime_type),
        case when count(transcoder_report_id) = 1 then max(audio_codec) else null end as audio_codec,
        case when count(transcoder_report_id) = 1 then max(video_codec) else null end as video_codec,
        max(creation_time) as creation_time,
        max(modification_time) as modification_time,
        max(detection_time) as detection_time,
        max(queueing_time) as queueing_time,
        max(transcoding_start_time) as transcoding_start_time,
        max(transcoding_finish_time) as transcoding_finish_time,
        max(total_cpu_time) as total_cpu_time,
        max(total_real_time) as total_real_time,
        case when count(transcoder_report_id) = 1 then max(attempt_count) else null end as attempt_count,
        case when count(transcoder_report_id) = 1 then max(machine_name) else null end as machine_name,
        case when count(transcoder_report_id) = 1 then max(worker_name) else null end as worker_name,
        max(failure_id) as failure_id, -- just to filter out NULLs
        max(outcome) as outcome, -- effectively an OR
        max(successful) as successful, -- effectively an OR
        case when count(transcoder_report_id) = 1 then max(comment) else null end as comment
from
        transcoder_reports
group by
        customer_id,
        profile_id,
        file_checksum;

create or replace view unique_transcoder_outcomes_per_profile as
select
        customer_id,
        profile_id,
        sum(case when outcome then 1 else 0 end) as successful_transcods,
        sum(case when (not outcome) then 1 else 0 end) as failed_transcods,
        sum(case when (not outcome) and (failure_id is null) then 1 else 0 end) as failed_unexpectedly_transcods
from
        unique_transcoder_reports
group by customer_id, profile_id;

create or replace view unique_internal_success_rate_per_profile as
select
        customer_id,
        profile_id,
        successful_transcods + failed_transcods as number_of_transcods,
        round(successful_transcods / (successful_transcods + failed_unexpectedly_transcods), 3) * 100 as success_rate
from unique_transcoder_outcomes_per_profile;
