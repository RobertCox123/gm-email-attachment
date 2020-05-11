from __future__ import print_function



import email

import zipfile

import os

import gzip

import string

import boto3

import urllib



print('Loading function')



s3 = boto3.client('s3')

s3r = boto3.resource('s3')

csvDir = "/tmp/output/"



outputBucket = ""  # Set here for a seperate bucket otherwise it is set to the events bucket

outputPrefix = “csv/“  # Should end with /





def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']

    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key']).decode('utf8')



    try:

        # Set outputBucket if required

        if not outputBucket:

            global outputBucket

            outputBucket = bucket



        # Use waiter to ensure the file is persisted

        waiter = s3.get_waiter('object_exists')

        waiter.wait(Bucket=bucket, Key=key)



        response = s3r.Bucket(bucket).Object(key)



        # Read the raw text file into a Email Object

        msg = email.message_from_string(response.get()["Body"].read())



        if len(msg.get_payload()) == 2:



            # Create directory for CSV files (makes debugging easier)

            if os.path.isdir(csvDir) == False:

                os.mkdir(csvDir)



            # The first attachment

            attachment = msg.get_payload()[1]



            # Extract the attachment into /tmp/output

            extract_attachment(attachment)



            # Upload the CSV files to S3

            upload_resulting_files_to_s3()



        else:

            print("Could not see file/attachment.")



        return 0

    except Exception as e:

        print(e)

        print('Error getting object {} from bucket {}. Make sure they exist '

            'and your bucket is in the same region as this '

            'function.'.format(key, bucket))

        raise e

    delete_file(key, bucket)

    



def extract_attachment(attachment):

    # Process filename.zip attachments

    if "gzip" in attachment.get_content_type():

        contentdisp = string.split(attachment.get('Content-Disposition'), '=')

        fname = contentdisp[1].replace('\"', '')

        open('/tmp/' + contentdisp[1], 'wb').write(attachment.get_payload(decode=True))

        # This assumes we have filename.csv.gz, if we get this wrong, we will just

        # ignore the report

        csvname = fname[:-3]

        open(csvDir + csvname, 'wb').write(gzip.open('/tmp/' + contentdisp[1], 'rb').read())



    # Process filename.csv.gz attachments (Providers not complying to standards)

    elif "zip" in attachment.get_content_type():

        open('/tmp/attachment.zip', 'wb').write(attachment.get_payload(decode=True))

        with zipfile.ZipFile('/tmp/attachment.zip', "r") as z:

            z.extractall(csvDir)



    else:

        print('Skipping ' + attachment.get_content_type())





def upload_resulting_files_to_s3():

    # Put all CSV back into S3 (Covers non-compliant cases if a ZIP contains multiple results)

    for fileName in os.listdir(csvDir):

        if fileName.endswith(".csv”):

            print("Uploading: " + fileName)  # File name to upload

            s3r.meta.client.upload_file(csvDir+'/'+fileName, outputBucket, outputPrefix+fileName)



            

# Delete the file in the current bucket

def delete_file(key, bucket):

    s3.delete_object(Bucket=bucket, Key=key)

    print("%s deleted fom %s ") % (key, bucket)
