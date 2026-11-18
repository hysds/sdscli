"""Single machine deployment (HC-672).

With SINGLE_MACHINE_CLUSTER: true every component runs from mozart's virtualenv and code under one
supervisord; each component keeps its own etc/log/run/bin folder. Unset, nothing changes.
"""

import os
import tempfile
import unittest
import unittest.mock as umock

import yaml


def _import_fabfile():
    """fabfile reads ~/.sds/config when imported; point it at a minimal config so the tests don't need a real one."""
    tmp = tempfile.mkdtemp()
    key = os.path.join(tmp, "key.pem")
    open(key, "w").close()
    cfg = {"OPS_HOME": "/home/ops", "OPS_USER": "ops", "KEY_FILENAME": key, "OTHER_VERDI_HOSTS": None}
    for name in ("MOZART", "METRICS", "GRQ", "FACTOTUM", "CI", "VERDI"):
        cfg["%s_PVT_IP" % name] = "10.0.0.1"
    for name in ("MOZART_RABBIT", "MOZART_REDIS", "MOZART_ES", "METRICS_REDIS", "METRICS_ES", "GRQ_ES"):
        cfg["%s_PVT_IP" % name] = "10.0.0.1"
    path = os.path.join(tmp, "config")
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f)
    with umock.patch("sdscli.conf_utils.get_user_config_path", return_value=path):
        from sdscli.adapters.hysds import fabfile
    return fabfile


def _shim_prompt_toolkit():
    """sdscli pins prompt-toolkit 1.x; newer versions dropped these names, which the command modules import."""
    import prompt_toolkit.shortcuts
    import prompt_toolkit.styles
    for module, name in ((prompt_toolkit.styles, "style_from_dict"), (prompt_toolkit.shortcuts, "print_tokens")):
        if not hasattr(module, name):
            setattr(module, name, lambda *args, **kwargs: None)


_shim_prompt_toolkit()
fab = _import_fabfile()
from sdscli.adapters.hysds import start, status, stop, update  # noqa: E402


class SingleMachineCase(unittest.TestCase):
    single = True

    def setUp(self):
        for patcher in (umock.patch.object(fab, "single_machine", self.single),
                        umock.patch.dict(fab.context, {"OPS_USER": "ops"})):
            patcher.start()
            self.addCleanup(patcher.stop)


class TestSetting(unittest.TestCase):

    def test_is_single_machine(self):
        for value in (True, "true", "True", " TRUE "):
            self.assertTrue(fab.is_single_machine({"SINGLE_MACHINE_CLUSTER": value}), value)
        for value in (False, "false", "False", None, ""):
            self.assertFalse(fab.is_single_machine({"SINGLE_MACHINE_CLUSTER": value}), value)
        self.assertFalse(fab.is_single_machine({}))


class TestFindConflicts(unittest.TestCase):

    def test_clean(self):
        confs = {"mozart": "[program:a]\nx=1\n", "sciflo": "[program:b]\n", "verdi": ""}
        self.assertEqual(fab.find_supervisord_conflicts(confs), [])

    def test_duplicate_program_across_components(self):
        confs = {"mozart": "[program:filebeats]\n", "sciflo": "[program:filebeats]\n", "metrics": "[program:x]\n"}
        problems = fab.find_supervisord_conflicts(confs)
        self.assertEqual(len(problems), 1)
        self.assertIn("[filebeats]", problems[0])
        self.assertIn("~/mozart", problems[0])
        self.assertIn("~/sciflo", problems[0])

    def test_duplicate_within_one_file_is_not_a_cross_component_conflict_but_is_reported(self):
        # supervisor itself rejects this; still worth flagging, same message
        problems = fab.find_supervisord_conflicts({"mozart": "[program:a]\n[program:a]\n"})
        self.assertEqual(len(problems), 1)

    def test_shared_sections(self):
        text = "[unix_http_server]\nfile=x\n[supervisord]\n[rpcinterface:supervisor]\n[program:a]\n"
        problems = fab.find_supervisord_conflicts({"sciflo": text})
        self.assertEqual(len(problems), 3)
        self.assertTrue(all("shared section" in p for p in problems))


class TestPaths(SingleMachineCase):

    def test_code_dir(self):
        for comp_dir in ("mozart", "sciflo", "metrics", "verdi"):
            self.assertEqual(fab.code_dir(comp_dir), "mozart")
        self.assertEqual(fab.code_dir("verdi-worker"), "verdi-worker")

    def test_code_dir_default(self):
        with umock.patch.object(fab, "single_machine", False):
            self.assertEqual(fab.code_dir("sciflo"), "sciflo")
            self.assertEqual(fab.code_dir("verdi"), "verdi")


class TestEnsureVenv(SingleMachineCase):

    def setUp(self):
        super().setUp()
        for name in ("exists", "mkdir", "run", "append", "prefix"):
            patcher = umock.patch.object(fab, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        patcher = umock.patch.object(fab, "abort", side_effect=SystemExit)
        self.abort = patcher.start()
        self.addCleanup(patcher.stop)

    def test_other_components_only_get_their_folders(self):
        self.exists.return_value = True  # ~/mozart installed
        fab.ensure_venv("sciflo")
        made = sorted(c.args[0] for c in self.mkdir.call_args_list)
        self.assertEqual(made, ["sciflo/bin", "sciflo/etc", "sciflo/log", "sciflo/run"])
        self.run.assert_not_called()
        self.append.assert_not_called()  # no `source ~/sciflo/bin/activate` in .bash_profile

    def test_requires_mozart(self):
        self.exists.return_value = False
        with self.assertRaises(SystemExit):
            fab.ensure_venv("verdi")
        self.assertIn("install.sh mozart", self.abort.call_args.args[0])
        self.mkdir.assert_not_called()

    def test_mozart_and_worker_staging_dir_still_get_a_venv(self):
        self.exists.return_value = False
        for hysds_dir in ("mozart", "verdi-worker"):
            self.run.reset_mock()
            fab.ensure_venv(hysds_dir)
            self.assertIn("virtualenv --system-site-packages %s" % hysds_dir, self.run.call_args_list[0].args[0])

    def test_default_creates_a_venv_per_component(self):
        self.exists.return_value = False
        with umock.patch.object(fab, "single_machine", False):
            fab.ensure_venv("sciflo")
        self.assertIn("virtualenv --system-site-packages sciflo", self.run.call_args_list[0].args[0])


class TestSupervisord(SingleMachineCase):

    def setUp(self):
        super().setUp()
        for name in ("exists", "mkdir", "run", "prefix", "check_supervisord_programs"):
            patcher = umock.patch.object(fab, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def commands(self):
        return [c.args[0] for c in self.run.call_args_list]

    def test_start_when_not_running_leaves_other_components_stopped(self):
        self.exists.return_value = False
        fab.grqd_start()
        self.check_supervisord_programs.assert_called_once()
        cmds = self.commands()
        self.assertEqual(cmds[0], "supervisord")
        self.assertEqual(sorted(cmds[1:]), ["supervisorctl stop factotum:*", "supervisorctl stop metrics:*",
                                            "supervisorctl stop mozart:*"])

    def test_start_when_running_only_starts_that_component(self):
        self.exists.return_value = True
        fab.verdid_start()
        self.assertEqual(self.commands(), ["supervisorctl reread", "supervisorctl update",
                                           "supervisorctl start factotum:*"])

    def test_start_all_when_running(self):
        self.exists.return_value = True
        fab.supervisord_start()
        self.assertEqual(self.commands()[-1], "supervisorctl start all")

    def test_stop_component(self):
        self.exists.return_value = True
        for stop_fn, group in ((fab.grqd_stop, "grq"), (fab.mozartd_stop, "mozart"),
                               (fab.metricsd_stop, "metrics"), (fab.verdid_stop, "factotum")):
            self.run.reset_mock()
            stop_fn()
            self.assertEqual(self.commands(), ["supervisorctl stop %s:*" % group])

    def test_stop_all_shuts_down(self):
        self.exists.return_value = True
        fab.supervisord_stop()
        self.assertEqual(self.commands(), ["supervisorctl shutdown"])

    def test_stop_when_not_running_is_a_noop(self):
        self.exists.return_value = False
        fab.grqd_stop()
        self.run.assert_not_called()

    def test_default_stop_shuts_down_the_component_supervisord(self):
        self.exists.return_value = True
        with umock.patch.object(fab, "single_machine", False):
            fab.grqd_stop()
        self.assertEqual(self.commands(), ["supervisorctl shutdown"])
        self.prefix.assert_called_with("source sciflo/bin/activate")


class TestKillHung(SingleMachineCase):

    def setUp(self):
        super().setUp()
        for name in ("run", "ps_x"):
            patcher = umock.patch.object(fab, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def commands(self):
        return [c.args[0] for c in self.run.call_args_list]

    def test_single_machine_leaves_only_mozart_monitors_alone(self):
        fab.kill_hung()
        job_worker, sfl_term, sfl_kill = self.commands()
        self.assertIn("grep -v -e sync_ec2_target_tracking_metric", job_worker)
        self.assertNotIn("$HOME/mozart/", job_worker)  # factotum runs from ~/mozart too
        self.assertNotIn("grep -v", sfl_term)
        self.assertNotIn("grep -v", sfl_kill)

    def test_default_skips_other_components_dirs(self):
        with umock.patch.object(fab, "single_machine", False):
            fab.kill_hung()
        for cmd in self.commands():
            self.assertIn('-e "$HOME/mozart/" -e "$HOME/sciflo/" -e "$HOME/metrics/"', cmd)


class TestSendSupervisordConf(SingleMachineCase):

    def setUp(self):
        super().setUp()
        patcher = umock.patch.object(update, "execute")
        self.execute = patcher.start()
        self.addCleanup(patcher.stop)

    def sent(self):
        return [c.args[1:3] for c in self.execute.call_args_list if c.args[0] is fab.send_template_user_override]

    def test_component_programs_go_to_programs_conf(self):
        update.send_supervisord_conf("grq", "supervisord.conf.grq", "sciflo")
        self.assertEqual(self.sent(), [("supervisord.conf.grq", "~/sciflo/etc/programs.conf")])

    def test_mozart_also_writes_the_main_file(self):
        update.send_supervisord_conf("mozart", "supervisord.conf.mozart", "mozart")
        self.assertEqual(self.sent(), [("supervisord.conf.single_machine", "~/mozart/etc/supervisord.conf"),
                                       ("supervisord.conf.mozart", "~/mozart/etc/programs.conf")])

    def test_default_writes_each_components_own_supervisord_conf(self):
        with umock.patch.object(fab, "single_machine", False):
            update.send_supervisord_conf("factotum", "supervisord.conf.factotum", "verdi")
            update.send_supervisord_conf("mozart", "supervisord.conf.mozart", "mozart")
        self.assertEqual(self.sent(), [("supervisord.conf.factotum", "~/verdi/etc/supervisord.conf"),
                                       ("supervisord.conf.mozart", "~/mozart/etc/supervisord.conf")])


class TestAll(SingleMachineCase):

    def test_start_all_starts_the_one_supervisord(self):
        with umock.patch.object(start, "execute") as execute, umock.patch.object(start, "start_grq") as start_grq:
            start.start_comp("all", None)
        start_grq.assert_not_called()
        self.assertIn(umock.call(fab.supervisord_start, roles=["mozart"]), execute.call_args_list)

    def test_stop_all_shuts_down_the_one_supervisord(self):
        with umock.patch.object(stop, "execute") as execute, umock.patch.object(stop, "stop_grq") as stop_grq:
            stop.stop_comp("all", None)
        stop_grq.assert_not_called()
        execute.assert_called_once_with(fab.supervisord_stop, roles=["mozart"])

    def test_status_lists_programs_once(self):
        with umock.patch.object(status, "print_status") as print_status:
            status.status_comp("all", None)
        shown = [c.args[3] for c in print_status.call_args_list if c.args[1] in ("grq", "mozart", "metrics", "factotum")]
        self.assertEqual(shown, [True, False, False, False])

    def test_default_start_all_starts_each_component(self):
        with umock.patch.object(fab, "single_machine", False), \
                umock.patch.object(start, "start_grq") as g, umock.patch.object(start, "start_mozart") as m, \
                umock.patch.object(start, "start_metrics") as me, umock.patch.object(start, "start_factotum") as f:
            start.start_comp("all", None)
        for fn in (g, m, me, f):
            fn.assert_called_once()

    def test_default_status_lists_programs_per_component(self):
        with umock.patch.object(fab, "single_machine", False), umock.patch.object(status, "print_status") as ps:
            status.status_comp("all", None)
        shown = [c.args[3] for c in ps.call_args_list if c.args[1] in ("grq", "mozart", "metrics", "factotum")]
        self.assertEqual(shown, [True, True, True, True])
