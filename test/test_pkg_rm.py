"""`sds pkg rm` code bucket guard (HC-627).

A containers index restored from another cluster carries that cluster's code
bucket URLs. `sds pkg rm` must not delete tarballs outside this cluster's
CODE_BUCKET; --keep-tarball removes only the index entries.
"""

import json
import unittest
import unittest.mock as umock
from argparse import Namespace

from sdscli.adapters.hysds import pkg

ENDPOINT = "s3-us-west-2.amazonaws.com"
OWN = f"s3://{ENDPOINT}/nisar-ops-cc-pop1"
FOREIGN = f"s3://{ENDPOINT}/nisar-ops-cc-blue"
TARBALL = "container-iems-sds_nisar-pcm:pcm_r05.01.2_pge_r05.01.2-1.tar.gz"
CONT_ID = "container-iems-sds_nisar-pcm:pcm_r05.01.2_pge_r05.01.2-1"


def container(**fields):
    return {"found": True, "_source": {"id": CONT_ID, **fields}}


def multi_arch(amd64_url, arm64_url):
    return json.dumps({"x86_64": amd64_url, "amd64": amd64_url,
                       "arm64": arm64_url, "aarch64": arm64_url})


class TestPkgRm(unittest.TestCase):

    def setUp(self):
        es_patcher = umock.patch.object(pkg, "mozart_es")
        self.es = es_patcher.start()
        self.addCleanup(es_patcher.stop)
        self.es.query.return_value = []

        rmall_patcher = umock.patch.object(pkg, "rmall")
        self.rmall = rmall_patcher.start()
        self.addCleanup(rmall_patcher.stop)

        conf_patcher = umock.patch.object(pkg, "SettingsConf")
        conf = conf_patcher.start()
        self.addCleanup(conf_patcher.stop)
        conf.return_value.get.side_effect = {
            "S3_ENDPOINT": ENDPOINT, "CODE_BUCKET": "nisar-ops-cc-pop1"}.get

    def rm(self, cont, keep_tarball=False):
        self.es.get_by_id.return_value = cont
        return pkg.rm(Namespace(id=CONT_ID, keep_tarball=keep_tarball))

    def assert_refused(self, result):
        self.assertEqual(result, 1)
        self.rmall.assert_not_called()
        self.es.delete_by_id.assert_not_called()

    def assert_docs_removed(self):
        self.es.delete_by_id.assert_any_call(index=pkg.CONTAINERS_INDEX, id=CONT_ID)

    def test_own_bucket_url_deleted(self):
        self.assertIsNone(self.rm(container(url=f"{OWN}/{TARBALL}")))
        self.rmall.assert_called_once_with(f"{OWN}/{TARBALL}")
        self.assert_docs_removed()

    def test_own_bucket_multi_arch_deletes_each_unique_url(self):
        amd64, arm64 = f"{OWN}/amd64.tar.gz", f"{OWN}/arm64.tar.gz"
        self.assertIsNone(self.rm(container(url=amd64, urls=multi_arch(amd64, arm64))))
        self.assertEqual(sorted(c.args[0] for c in self.rmall.call_args_list), [amd64, arm64])
        self.assert_docs_removed()

    def test_foreign_bucket_url_refused(self):
        """The NSDS-5295 case: a doc restored from FWD points at FWD's bucket."""
        self.assert_refused(self.rm(container(url=f"{FOREIGN}/{TARBALL}")))

    def test_mixed_multi_arch_refused_before_any_delete(self):
        urls = multi_arch(f"{OWN}/amd64.tar.gz", f"{FOREIGN}/arm64.tar.gz")
        self.assert_refused(self.rm(container(urls=urls)))

    def test_bucket_name_prefix_is_not_a_match(self):
        self.assert_refused(self.rm(container(url=f"{OWN}-old/{TARBALL}")))

    def test_bucket_first_url_refused(self):
        self.assert_refused(self.rm(container(url=f"s3://nisar-ops-cc-pop1/{TARBALL}")))

    def test_malformed_urls_refused(self):
        self.assert_refused(self.rm(container(urls="{not json", url=f"{OWN}/{TARBALL}")))

    def test_keep_tarball_removes_only_index_entries(self):
        self.assertIsNone(self.rm(container(url=f"{FOREIGN}/{TARBALL}"), keep_tarball=True))
        self.rmall.assert_not_called()
        self.assert_docs_removed()

    def test_keep_tarball_with_malformed_urls_removes_index_entries(self):
        self.assertIsNone(self.rm(container(urls="{not json"), keep_tarball=True))
        self.rmall.assert_not_called()
        self.assert_docs_removed()

    def test_keep_tarball_removes_job_specs_and_hysds_ios(self):
        job_spec = {"id": "job-SCIFLO_GSLC:pcm_r05.01.2_pge_r05.01.2-1"}
        hysds_io = {"id": "hysds-io-SCIFLO_GSLC:pcm_r05.01.2_pge_r05.01.2-1"}
        self.es.query.side_effect = [[{"_source": job_spec}], [{"_source": hysds_io}], []]
        self.rm(container(url=f"{FOREIGN}/{TARBALL}"), keep_tarball=True)
        self.es.delete_by_id.assert_any_call(index=pkg.JOB_SPECS_INDEX, id=job_spec["id"])
        self.es.delete_by_id.assert_any_call(index=pkg.HYSDS_IOS_MOZART_INDEX, id=hysds_io["id"])

    def test_no_urls_removes_index_entries(self):
        self.assertIsNone(self.rm(container()))
        self.rmall.assert_not_called()
        self.assert_docs_removed()

    def test_not_found(self):
        self.assertEqual(self.rm({"found": False}), 1)
        self.es.delete_by_id.assert_not_called()


if __name__ == "__main__":
    unittest.main()
