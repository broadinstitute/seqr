

# validate function ( vcf, assembly, project_id=None )

 #1. don't create any records yet
 #2. check that the callset or set of files is valid
 #3. return info, warning, error - info: # of samples that will have data, error: couldn't parse


# create dataset function  ( new_dataset name, vcf )
 #1. create dataset / SampleBatch record if it doesn't exist
 #       - grant permission to owner, and to project view group
 #2. create Sample records with sample ids from the file
 # return dataset id

# attach dataset to project ( sample_batch_id, project_id )

# load sample batch ( sample_batch_id ):
    #0. record 'started loading' event
    #1. update SampleBatch loading status
    #2. queue loading on cluster (or create new cluster?)
        # - copy to seqr cloud drive
        # - generate VEP annotated version
        # - load into database
        # - mark all samples as loaded  in database
        # - if error - mark as error
        # - if no new datasets to load since 5 minutes ago, delete the cluster.
    #3. record 'finished loading' event



# def _validate():


"""
Task

user
created_date
task_type
task_status

"""