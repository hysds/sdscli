"""SDS package management functions."""
from datetime import datetime
from future import standard_library
standard_library.install_aliases()

import os
import json
import tarfile
import shutil

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.os_utils import validate_dir, normpath

from osaka.main import get, put, rmall
from hysds.es_util import get_mozart_es
from hysds.utils import datetime_iso_naive

CONTAINERS_INDEX = "containers"
JOB_SPECS_INDEX = "job_specs"
HYSDS_IOS_MOZART_INDEX = "hysds_ios-mozart"
HYSDS_IOS_GRQ_INDEX = "hysds_ios-grq"
USER_RULES_MOZART_INDEX = 'user_rules-mozart'
USER_RULES_GRQ_INDEX = 'user_rules-grq'

mozart_es = get_mozart_es()


def ls(args):
    """List HySDS packages."""
    hits = mozart_es.query(index=CONTAINERS_INDEX)  # query for containers

    for hit in hits:
        logger.debug(json.dumps(hit, indent=2))
        print(hit['_id'])
    return


def export(args):
    """Export HySDS package."""
    cont_id = args.id  # container id

    # query for container
    cont = mozart_es.get_by_id(index=CONTAINERS_INDEX, id=cont_id, ignore=404)
    if cont['found'] is False:
        logger.error(f"SDS package id {cont_id} not found.")
        return 1

    cont_info = cont['_source']
    logger.debug("cont_info: %s" % json.dumps(cont_info, indent=2))

    # set export directory
    outdir = normpath(args.outdir)
    export_name = "{}.sdspkg".format(cont_id.replace(':', '-'))
    export_dir = os.path.join(outdir, export_name)
    logger.debug("export_dir: %s" % export_dir)

    if os.path.exists(export_dir):  # if directory exists, stop
        logger.error(f"SDS package export directory {export_dir} exists. Not continuing.")
        return 1

    validate_dir(export_dir)  # create export directory

    # download container(s) - handle both multi-arch (urls) and legacy (url)
    if cont_info.get('urls'):
        try:
            urls_dict = json.loads(cont_info['urls'])
            # Download all unique architecture-specific containers
            unique_urls = set(urls_dict.values())
            downloaded_files = {}
            for url in unique_urls:
                logger.info(f"Downloading container: {url}")
                get(url, export_dir)
                downloaded_files[url] = os.path.basename(url)
            
            # Update urls dict with local filenames
            updated_urls = {}
            for arch, url in urls_dict.items():
                updated_urls[arch] = downloaded_files[url]
            cont_info['urls'] = json.dumps(updated_urls)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse urls field: {e}")
    elif cont_info.get('url', None) != None:
        # Legacy single-arch container
        get(cont_info['url'], export_dir)
        cont_info['url'] = os.path.basename(cont_info['url'])

    query = {
        "query": {
            "term": {"container.keyword": cont_id}  # query job specs
        }
    }
    job_specs = mozart_es.query(index=JOB_SPECS_INDEX, body=query)
    job_specs = [job_spec['_source'] for job_spec in job_specs]
    logger.debug("job_specs: %s" % json.dumps(job_specs, indent=2))

    # backwards-compatible query
    if len(job_specs) == 0:
        logger.debug("Got no job_specs. Checking deprecated mappings:")
        query = {
            "query": {
                "query_string": {
                    "query": f"container:\"{cont_id}\""
                }
            }
        }
        job_specs = mozart_es.query(index=JOB_SPECS_INDEX, body=query)
        job_specs = [job_spec['_source'] for job_spec in job_specs]
        logger.debug("job_specs: %s" % json.dumps(job_specs, indent=2))

    hysds_ios = []  # pull hysds_ios for each job_spec and download any dependency images
    dep_images = {}
    for job_spec in job_specs:
        # download dependency images - handle both multi-arch (container_image_urls) and legacy (container_image_url)
        for d in job_spec.get('dependency_images', []):
            dep_name = d['container_image_name']
            if dep_name in dep_images:
                # Already processed this dependency - reuse cached values
                cached = dep_images[dep_name]
                if 'container_image_urls' in cached:
                    d['container_image_urls'] = cached['container_image_urls']
                if 'container_image_url' in cached:
                    d['container_image_url'] = cached['container_image_url']
            else:
                # Handle multi-arch dependency images
                if d.get('container_image_urls'):
                    try:
                        urls_dict = json.loads(d['container_image_urls'])
                        unique_urls = set(urls_dict.values())
                        downloaded_files = {}
                        for url in unique_urls:
                            if args.skip_include_dependency_images:
                                logger.info(f"Skipping download of dependency image: {url}")
                                downloaded_files[url] = os.path.basename(url)
                            else:
                                logger.info(f"Downloading dependency image: {url}")
                                get(url, export_dir)
                                downloaded_files[url] = os.path.basename(url)
                        
                        # Update urls dict with local filenames
                        updated_urls = {}
                        for arch, url in urls_dict.items():
                            updated_urls[arch] = downloaded_files[url]
                        d['container_image_urls'] = json.dumps(updated_urls)
                        dep_images[dep_name] = {'container_image_urls': d['container_image_urls']}
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.error(f"Failed to parse container_image_urls field for dependency: {e}")
                # Handle legacy single-arch dependency images
                elif d.get('container_image_url'):
                    if args.skip_include_dependency_images:
                        logger.info(f"Skipping download of dependency image: {d['container_image_url']}")
                    else:
                        get(d['container_image_url'], export_dir)
                    d['container_image_url'] = os.path.basename(d['container_image_url'])
                    dep_images[dep_name] = {'container_image_url': d['container_image_url']}

        # collect hysds_ios from mozart
        query = {
            "query": {
                "term": {"job-specification.keyword": job_spec['id']}
            }
        }
        mozart_hysds_ios = mozart_es.query(index=HYSDS_IOS_MOZART_INDEX, body=query)
        mozart_hysds_ios = [hysds_io['_source'] for hysds_io in mozart_hysds_ios]
        logger.debug("Found %d hysds_ios on mozart for %s." % (len(mozart_hysds_ios), job_spec['id']))

        # backwards-compatible query
        if len(mozart_hysds_ios) == 0:
            logger.debug("Got no hysds_ios from mozart. Checking deprecated mappings:")
            query = {
                "query": {
                    "query_string": {
                        "query": "job-specification:\"{}\"".format(job_spec['id'])
                    }
                }
            }
            mozart_hysds_ios = mozart_es.query(index=HYSDS_IOS_MOZART_INDEX, body=query)
            mozart_hysds_ios = [hysds_io['_source'] for hysds_io in mozart_hysds_ios]
            logger.debug("Found %d hysds_ios on mozart for %s." % (len(mozart_hysds_ios), job_spec['id']))
        hysds_ios.extend(mozart_hysds_ios)

        # collect hysds_ios from grq
        query = {
            "query": {
                "term": {"job-specification.keyword": job_spec['id']}
            }
        }
        grq_hysds_ios = mozart_es.query(index=HYSDS_IOS_GRQ_INDEX, body=query)
        grq_hysds_ios = [hysds_io['_source'] for hysds_io in grq_hysds_ios]
        logger.debug("Found %d hysds_ios on grq for %s." % (len(grq_hysds_ios), job_spec['id']))

        # backwards-compatible query
        if len(mozart_hysds_ios) == 0:
            logger.debug("Got no hysds_ios from grq. Checking deprecated mappings:")
            query = {
                "query": {
                    "query_string": {
                        "query": "job-specification:\"{}\"".format(job_spec['id'])
                    }
                }
            }
            grq_hysds_ios = mozart_es.query(index=HYSDS_IOS_GRQ_INDEX, body=query)
            grq_hysds_ios = [hysds_io['_source'] for hysds_io in grq_hysds_ios]
            logger.debug("Found %d hysds_ios on grq for %s." % (len(grq_hysds_ios), job_spec['id']))

        hysds_ios.extend(grq_hysds_ios)
    logger.debug("Found %d hysds_ios total." % (len(hysds_ios)))

    # export allowed accounts
    if not args.accounts:
        for hysds_io in hysds_ios:
            if 'allowed_accounts' in hysds_io:
                del hysds_io['allowed_accounts']

    # dump manifest JSON
    manifest = {
        "containers": cont_info,
        "job_specs": job_specs,
        "hysds_ios": hysds_ios,
    }
    manifest_file = os.path.join(export_dir, 'manifest.json')
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    # tar up hysds package
    tar_file = os.path.join(outdir, f"{export_name}.tar")
    with tarfile.open(tar_file, "w") as tar:
        tar.add(export_dir, arcname=os.path.relpath(export_dir, outdir))

    shutil.rmtree(export_dir)  # remove package dir


def import_pkg(args):
    """Import HySDS package."""

    conf = SettingsConf()  # get user's SDS conf settings

    # package tar file
    tar_file = normpath(args.file)
    if not os.path.isfile(tar_file):
        logger.error("HySDS package file %s doesn't exist." % tar_file)
        return 1
    logger.debug("tar_file: %s" % tar_file)

    # extract
    outdir = os.path.dirname(tar_file)
    with tarfile.open(tar_file) as tar:
        export_name = tar.getnames()[0]
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tar, outdir)
    export_dir = os.path.join(outdir, export_name)
    logger.debug("export_dir: %s" % export_dir)

    # detect export dir
    if not os.path.isdir(export_dir):
        logger.error("Cannot find HySDS package dir %s." % export_dir)
        return 1

    # read in manifest
    manifest_file = os.path.join(export_dir, 'manifest.json')
    with open(manifest_file) as f:
        manifest = json.load(f)
    logger.debug("manifest: %s" % json.dumps(manifest, indent=2, sort_keys=True))

    # get code bucket
    code_bucket = conf.get('CODE_BUCKET')
    code_bucket_url = "s3://{}/{}".format(conf.get('S3_ENDPOINT'), code_bucket)
    logger.debug("code_bucket: %s" % code_bucket)
    logger.debug("code_bucket_url: %s" % code_bucket_url)

    cont_info = manifest['containers']

    # upload container image(s) to s3 - handle both multi-arch (urls) and legacy (url)
    if cont_info.get('urls'):
        try:
            urls_dict = json.loads(cont_info['urls'])
            # Upload all unique architecture-specific containers
            unique_files = set(urls_dict.values())
            uploaded_urls = {}
            for filename in unique_files:
                cont_image = os.path.join(export_dir, filename)
                s3_url = "{}/{}".format(code_bucket_url, filename)
                logger.info(f"Uploading container: {filename} to {s3_url}")
                put(cont_image, s3_url)
                uploaded_urls[filename] = s3_url
            
            # Update urls dict with S3 URLs
            updated_urls = {}
            for arch, filename in urls_dict.items():
                updated_urls[arch] = uploaded_urls[filename]
            cont_info['urls'] = json.dumps(updated_urls)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse urls field: {e}")
    elif cont_info.get('url', None) != None:
        # Legacy single-arch container
        cont_image = os.path.join(export_dir, cont_info['url'])
        cont_info['url'] = "{}/{}".format(code_bucket_url, cont_info['url'])
        put(cont_image, cont_info['url'])

    # index container in ES
    indexed_container = mozart_es.index_document(index=CONTAINERS_INDEX, body=cont_info, id=cont_info['id'])
    logger.debug(indexed_container)

    # index job_specs in ES and upload any dependency containers
    dep_images = {}
    for job_spec in manifest['job_specs']:
        # upload dependency images - handle both multi-arch (container_image_urls) and legacy (container_image_url)
        for d in job_spec.get('dependency_images', []):
            dep_name = d['container_image_name']
            if dep_name in dep_images:
                # Already processed this dependency - reuse cached values
                cached = dep_images[dep_name]
                if 'container_image_urls' in cached:
                    d['container_image_urls'] = cached['container_image_urls']
                if 'container_image_url' in cached:
                    d['container_image_url'] = cached['container_image_url']
            else:
                # Handle multi-arch dependency images
                if d.get('container_image_urls'):
                    try:
                        urls_dict = json.loads(d['container_image_urls'])
                        unique_files = set(urls_dict.values())
                        uploaded_urls = {}
                        for filename in unique_files:
                            dep_img = os.path.join(export_dir, filename)
                            s3_url = "{}/{}".format(code_bucket_url, filename)
                            if args.skip_include_dependency_images:
                                logger.info(f"Skipping upload of dependency image: {dep_img}")
                            else:
                                logger.info(f"Uploading dependency image: {filename} to {s3_url}")
                                put(dep_img, s3_url)
                            uploaded_urls[filename] = s3_url
                        
                        # Update urls dict with S3 URLs
                        updated_urls = {}
                        for arch, filename in urls_dict.items():
                            updated_urls[arch] = uploaded_urls[filename]
                        d['container_image_urls'] = json.dumps(updated_urls)
                        dep_images[dep_name] = {'container_image_urls': d['container_image_urls']}
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.error(f"Failed to parse container_image_urls field for dependency: {e}")
                # Handle legacy single-arch dependency images
                elif d.get('container_image_url'):
                    dep_img = os.path.join(export_dir, d['container_image_url'])
                    d['container_image_url'] = "{}/{}".format(code_bucket_url, d['container_image_url'])
                    if args.skip_include_dependency_images:
                        logger.info(f"Skipping upload of dependency image: {dep_img}")
                    else:
                        put(dep_img, d['container_image_url'])
                    dep_images[dep_name] = {'container_image_url': d['container_image_url']}

        indexed_job_spec = mozart_es.index_document(index=JOB_SPECS_INDEX, body=job_spec, id=job_spec['id'])
        logger.debug(indexed_job_spec)

    # index hysds_ios to ES
    for hysds_io in manifest['hysds_ios']:
        component = hysds_io.get('component', 'tosca')

        hysds_io_id = hysds_io['id']
        if component in ('mozart', 'figaro'):
            indexed_hysds_io = mozart_es.index_document(index=HYSDS_IOS_MOZART_INDEX, body=hysds_io, id=hysds_io_id)
            logger.debug(indexed_hysds_io)
        else:
            indexed_hysds_io = mozart_es.index_document(index=HYSDS_IOS_GRQ_INDEX, body=hysds_io, id=hysds_io_id)
            logger.debug(indexed_hysds_io)

    # index user_rules to ES
    for component in (('mozart', USER_RULES_MOZART_INDEX), ('grq', USER_RULES_GRQ_INDEX)):
        for rule in manifest.get('user_rules', {}).get(component[0], []):
            now = datetime_iso_naive() + 'Z'

            if not rule.get('creation_time', None):
                rule['creation_time'] = now
            if not rule.get('modified_time', None):
                rule['modified_time'] = now

            result = mozart_es.index_document(index=component[1], body=rule)  # indexing user rules
            logger.debug(result)

    shutil.rmtree(export_dir)  # remove package dir


def rm(args):
    """Remove HySDS package."""
    cont_id = args.id  # container id

    cont_info = mozart_es.get_by_id(index=CONTAINERS_INDEX, id=cont_id, ignore=404)  # query for container
    if cont_info['found'] is False:
        logger.error(f"SDS package id {cont_id} not found.")
        return 1

    cont_info = cont_info['_source']
    logger.debug(f"cont_info: {json.dumps(cont_info, indent=2)}")

    # Delete all architecture-specific containers if urls field exists
    if cont_info.get('urls'):
        try:
            urls_dict = json.loads(cont_info['urls'])
            # Get unique URLs (avoid deleting same URL multiple times)
            unique_urls = set(urls_dict.values())
            for url in unique_urls:
                logger.info(f"Deleting container: {url}")
                rmall(url)  # delete container from code bucket and ES
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse urls field: {e}")
    # Fallback to legacy url field for backward compatibility
    elif cont_info.get('url'):
        rmall(cont_info['url'])  # delete container from code bucket and ES
    else:
        logger.info(f"No container URLs found, skipping deletion from code bucket")

    deleted_container = mozart_es.delete_by_id(index=CONTAINERS_INDEX, id=cont_info['id'])
    logger.debug(deleted_container)

    query = {
        "query": {
            "term": {"container.keyword": cont_id}  # query job specs
        }
    }

    job_specs = mozart_es.query(index=JOB_SPECS_INDEX, body=query)
    job_specs = [job_spec['_source'] for job_spec in job_specs]
    logger.debug("job_specs: %s" % json.dumps(job_specs, indent=2))

    # delete job_specs and hysds_ios
    for job_spec in job_specs:
        query = {
            "query": {
                "term": {"job-specification.keyword": job_spec['id']}  # collect hysds_ios from mozart
            }
        }
        mozart_hysds_ios = mozart_es.query(index=HYSDS_IOS_MOZART_INDEX, body=query)
        mozart_hysds_ios = [hysds_io['_source'] for hysds_io in mozart_hysds_ios]
        logger.debug("Found %d hysds_ios on mozart for %s" % (len(mozart_hysds_ios), job_spec['id']))

        for hysds_io in mozart_hysds_ios:  # deleting hysds_io in mozart
            hysds_io_id = hysds_io['id']
            deleted_hysds_io = mozart_es.delete_by_id(index=HYSDS_IOS_MOZART_INDEX, id=hysds_io_id)
            logger.debug(deleted_hysds_io)

        query = {
            "query": {
                "term": {"job-specification.keyword": job_spec['id']}  # collect hysds_ios from GRQ
            }
        }
        grq_hysds_ios = mozart_es.query(index=HYSDS_IOS_GRQ_INDEX, body=query)
        grq_hysds_ios = [hysds_io['_source'] for hysds_io in grq_hysds_ios]
        logger.debug("Found %d hysds_ios on grq for %s." % (len(grq_hysds_ios), job_spec['id']))

        for hysds_io in grq_hysds_ios:
            hysds_io_id = hysds_io['id']
            deleted_hysds_io = mozart_es.delete_by_id(index=HYSDS_IOS_GRQ_INDEX, id=hysds_io_id)
            logger.debug(deleted_hysds_io)

        deleted_job_spec = mozart_es.delete_by_id(index=JOB_SPECS_INDEX, id=job_spec['id'])  # delete job_spec from ES
        logger.debug(deleted_job_spec)
