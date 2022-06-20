import datetime
import os
import tempfile

from unittest import mock
import yaml

from . import utils

from hotsos.core.issues import IssuesManager
from hotsos.core.issues.utils import IssuesStore
from hotsos.core.config import setup_config, HotSOSConfig
from hotsos.core.searchtools import FileSearcher, SearchDef
from hotsos.core import ycheck
from hotsos.core.ycheck import (
    events,
    scenarios,
)
from hotsos.core.ycheck.engine import (
    CallbackHelper,
    YDefsSection,
    YDefsLoader,
)
from hotsos.core.ycheck.engine.properties_common import (
    YPropertyBase,
    cached_yproperty_attr,
)
from hotsos.core.ycheck.engine.properties import YPropertyCheck


class TestProperty(YPropertyBase):

    @cached_yproperty_attr
    def myattr(self):
        return '123'

    @property
    def myotherattr(self):
        return '456'

    @property
    def always_true(self):
        return True

    @property
    def always_false(self):
        return False


class FakeServiceObjectManager(object):

    def __init__(self, start_times):
        self._start_times = start_times

    def __call__(self, name, state):
        return FakeServiceObject(name, state,
                                 start_time=self._start_times[name])


class FakeServiceObject(object):

    def __init__(self, name, state, start_time):
        self.name = name
        self.state = state
        self.start_time = start_time


YDEF_NESTED_LOGIC = """
checks:
  isTrue:
    requires:
      and:
        - property: tests.unit.test_ycheck.TestProperty.always_true
        - property:
            path: tests.unit.test_ycheck.TestProperty.always_false
            ops: [[not_]]
  isalsoTrue:
    requires:
      or:
        - property: tests.unit.test_ycheck.TestProperty.always_true
        - property: tests.unit.test_ycheck.TestProperty.always_false
  isstillTrue:
    requires:
      and:
        - property: tests.unit.test_ycheck.TestProperty.always_true
      or:
        - property: tests.unit.test_ycheck.TestProperty.always_true
        - property: tests.unit.test_ycheck.TestProperty.always_false
  isnotTrue:
    requires:
      and:
        - property: tests.unit.test_ycheck.TestProperty.always_true
      or:
        - property: tests.unit.test_ycheck.TestProperty.always_false
        - property: tests.unit.test_ycheck.TestProperty.always_false
conclusions:
  conc1:
    decision:
      and:
        - isTrue
        - isalsoTrue
      or:
        - isstillTrue
    raises:
      type: IssueTypeBase
      message: conc1
  conc2:
    decision:
      and:
        - isTrue
        - isnotTrue
      or:
        - isalsoTrue
    raises:
      type: IssueTypeBase
      message: conc2
  conc3:
    decision:
      not:
        - isnotTrue
      or:
        - isalsoTrue
    raises:
      type: IssueTypeBase
      message: conc3
"""


YAML_DEF_W_INPUT = """
pluginX:
  groupA:
    input:
      path: foo/bar1
    sectionA:
      artifactX:
        requires:
          apt: foo
"""

YAML_DEF_REQUIRES_APT = """
pluginX:
  groupA:
    requires:
      apt:
        mypackage:
          - min: '3.0'
            max: '3.2'
          - min: '4.0'
            max: '4.2'
          - min: '5.0'
            max: '5.2'
        altpackage:
          - min: '3.0'
            max: '3.2'
          - min: '4.0'
            max: '4.2'
          - min: '5.0'
            max: '5.2'
"""


YAML_DEF_REQUIRES_SYSTEMD_PASS_1 = """
pluginX:
  groupA:
    requires:
      systemd:
        ondemand: enabled
        nova-compute: enabled
"""


YAML_DEF_REQUIRES_SYSTEMD_STARTED_AFTER = """
pluginX:
  groupA:
    requires:
      systemd:
        openvswitch-switch:
          state: enabled
          started-after: neutron-openvswitch-agent
"""


YAML_DEF_REQUIRES_SYSTEMD_FAIL_1 = """
pluginX:
  groupA:
    requires:
      systemd:
        ondemand: enabled
        nova-compute: disabled
"""

YAML_DEF_REQUIRES_MAPPED = """
myplugin:
  myscenario:
    checks:
      is_exists_mapped:
        systemd: nova-compute
      is_exists_unmapped:
        requires:
          systemd: nova-compute
"""

YAML_DEF_REQUIRES_SYSTEMD_FAIL_2 = """
pluginX:
  groupA:
    requires:
      systemd:
        ondemand:
          state: enabled
        nova-compute:
          state: disabled
          op: eq
"""


YAML_DEF_REQUIRES_GROUPED = """
passdef1:
  requires:
    - path: sos_commands/networking
    - not:
        path: sos_commands/networking_foo
    - apt: python3.8
    - and:
        - apt:
            systemd:
              - min: '245.4-4ubuntu3.14'
                max: '245.4-4ubuntu3.15'
      or:
        - apt: nova-compute
      not:
        - apt: blah
passdef2:
  requires:
    and:
      - apt: systemd
    or:
      - apt: nova-compute
    not:
      - apt: blah
faildef1:
  requires:
    - path: sos_commands/networking_foo
    - and:
        - apt: doo
        - apt: daa
      or:
        - apt: nova-compute
      not:
        - apt: blah
        - apt: nova-compute
faildef2:
  requires:
    - apt: python3.8
    - apt: python1.0
"""

YAML_DEF_W_INPUT_SUPERSEDED = """
pluginX:
  groupA:
    input:
      path: foo/bar1
    sectionA:
      input:
        path: foo/bar2
      artifactX:
        requires:
          apt: foo
"""

YAML_DEF_W_INPUT_SUPERSEDED2 = """
pluginX:
  groupA:
    input:
      path: foo/bar1
    sectionA:
      input:
        path: foo/bar2
      artifactX:
        input:
          path: foo/bar3
        requires:
          apt: foo
"""

YAML_DEF_EXPR_TYPES = r"""
myplugin:
  mygroup:
    input:
      path: {path}
    section1:
      my-sequence-search:
        start: '^hello'
        body: '^\S+'
        end: '^world'
      my-passthrough-search:
        passthrough-results: True
        start: '^hello'
        end: '^world'
      my-pass-search:
        expr: '^hello'
        hint: '.+'
      my-fail-search1:
        expr: '^hello'
        hint: '^foo'
      my-fail-search2:
        expr: '^foo'
        hint: '.+'
"""  # noqa


SCENARIO_W_ERROR = r"""
myplugin:
  scenarioA:
    checks:
      property_no_error:
        property: tests.unit.test_ycheck.TestProperty.always_true
    conclusions:
      c1:
        decision: property_no_error
        raises:
          type: SystemWarning
          message: foo
  scenarioB:
    checks:
      property_w_error:
        property: tests.unit.test_ycheck.TestProperty.i_dont_exist
    conclusions:
      c1:
        decision: property_w_error
        raises:
          type: SystemWarning
          message: foo
"""  # noqa


SCENARIO_CHECKS = r"""
myplugin:
  myscenario:
    checks:
      logmatch:
        input:
          path: foo.log
        expr: '^([0-9-]+)\S* (\S+) .+'
        check-parameters:
          min-results: 3
          search-period-hours: 24
          search-result-age-hours: 48
      property_true_shortform:
        requires:
          property: hotsos.core.plugins.system.SystemBase.virtualisation_type
      property_has_value_longform:
        requires:
          property:
            path: hotsos.core.plugins.system.SystemBase.virtualisation_type
            ops: [[eq, kvm], [truth], [not_], [not_]]
      apt_pkg_exists:
        requires:
          apt: nova-compute
      snap_pkg_exists:
        requires:
          snap: core20
      service_exists_short:
        requires:
          systemd: nova-compute
      service_exists_and_enabled:
        requires:
          systemd:
            nova-compute: enabled
      service_exists_not_enabled:
        requires:
          systemd:
            nova-compute:
              state: enabled
              op: ne
    conclusions:
      justlog:
        priority: 1
        decision: logmatch
        raises:
          type: SystemWarning
          message: log matched {num} times
          format-dict:
            num: '@checks.logmatch.search.results:len'
      logandsnap:
        priority: 2
        decision:
          and:
            - logmatch
            - snap_pkg_exists
        raises:
          type: SystemWarning
          message: log matched {num} times and snap exists
          format-dict:
            num: '@checks.logmatch.search.results:len'
      logandsnapandservice:
        priority: 3
        decision:
          and:
            - logmatch
            - snap_pkg_exists
            - service_exists_short
            - service_exists_and_enabled
            - property_true_shortform
            - property_has_value_longform
        raises:
          type: SystemWarning
          message: log matched {num} times, snap and service exists
          format-dict:
            num: '@checks.logmatch.search.results:len'
"""  # noqa


class TestYamlChecks(utils.BaseTestCase):

    def test_yproperty_attr_cache(self):
        p = TestProperty()
        self.assertEqual(getattr(p.cache, '__yproperty_attr__myattr'), None)
        self.assertEqual(p.myattr, '123')
        self.assertEqual(getattr(p.cache, '__yproperty_attr__myattr'), '123')
        self.assertEqual(p.myattr, '123')
        self.assertEqual(p.myotherattr, '456')

    def test_yaml_def_group_input(self):
        plugin_checks = yaml.safe_load(YAML_DEF_W_INPUT).get('pluginX')
        for name, group in plugin_checks.items():
            group = YDefsSection(name, group)
            for entry in group.leaf_sections:
                self.assertEqual(entry.input.path,
                                 os.path.join(HotSOSConfig.DATA_ROOT,
                                              'foo/bar1*'))

    def test_yaml_def_requires_grouped(self):
        mydef = YDefsSection('mydef',
                             yaml.safe_load(YAML_DEF_REQUIRES_GROUPED))
        tested = 0
        for entry in mydef.leaf_sections:
            if entry.name == 'passdef1':
                tested += 1
                self.assertTrue(entry.requires.passes)
            elif entry.name == 'passdef2':
                tested += 1
                self.assertTrue(entry.requires.passes)
            elif entry.name == 'faildef1':
                tested += 1
                self.assertFalse(entry.requires.passes)
            elif entry.name == 'faildef2':
                tested += 1
                self.assertFalse(entry.requires.passes)

        self.assertEqual(tested, 4)

    def test_yaml_def_section_input_override(self):
        plugin_checks = yaml.safe_load(YAML_DEF_W_INPUT_SUPERSEDED)
        for name, group in plugin_checks.get('pluginX').items():
            group = YDefsSection(name, group)
            for entry in group.leaf_sections:
                self.assertEqual(entry.input.path,
                                 os.path.join(HotSOSConfig.DATA_ROOT,
                                              'foo/bar2*'))

    def test_yaml_def_entry_input_override(self):
        plugin_checks = yaml.safe_load(YAML_DEF_W_INPUT_SUPERSEDED2)
        for name, group in plugin_checks.get('pluginX').items():
            group = YDefsSection(name, group)
            for entry in group.leaf_sections:
                self.assertEqual(entry.input.path,
                                 os.path.join(HotSOSConfig.DATA_ROOT,
                                              'foo/bar3*'))

    def test_yaml_def_entry_seq(self):
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(DATA_ROOT=dtmp)
            data_file = os.path.join(dtmp, 'data.txt')
            _yaml = YAML_DEF_EXPR_TYPES.format(
                                             path=os.path.basename(data_file))
            open(os.path.join(dtmp, 'events.yaml'), 'w').write(_yaml)
            open(data_file, 'w').write('hello\nbrave\nworld\n')
            plugin_checks = yaml.safe_load(_yaml).get('myplugin')
            for name, group in plugin_checks.items():
                group = YDefsSection(name, group)
                for entry in group.leaf_sections:
                    self.assertEqual(entry.input.path,
                                     '{}*'.format(data_file))

            test_self = self
            match_count = {'count': 0}
            callbacks_called = {}
            setup_config(PLUGIN_YAML_DEFS=dtmp, PLUGIN_NAME='myplugin')
            EVENTCALLBACKS = CallbackHelper()

            class MyEventHandler(events.YEventCheckerBase):
                def __init__(self):
                    super().__init__(yaml_defs_group='mygroup',
                                     searchobj=FileSearcher(),
                                     callback_helper=EVENTCALLBACKS)

                @EVENTCALLBACKS.callback()
                def my_sequence_search(self, event):
                    callbacks_called[event.name] = True
                    for section in event.results:
                        for result in section:
                            if result.tag.endswith('-start'):
                                match_count['count'] += 1
                                test_self.assertEqual(result.get(0), 'hello')
                            elif result.tag.endswith('-body'):
                                match_count['count'] += 1
                                test_self.assertEqual(result.get(0), 'brave')
                            elif result.tag.endswith('-end'):
                                match_count['count'] += 1
                                test_self.assertEqual(result.get(0), 'world')

                @EVENTCALLBACKS.callback()
                def my_passthrough_search(self, event):
                    # expected to be passthough results (i.e. raw)
                    callbacks_called[event.name] = True
                    tag = '{}-start'.format(event.search_tag)
                    start_results = event.results.find_by_tag(tag)
                    test_self.assertEqual(start_results[0].get(0), 'hello')

                @EVENTCALLBACKS.callback('my-pass-search',
                                         'my-fail-search1',
                                         'my-fail-search2')
                def my_standard_search_common(self, event):
                    callbacks_called[event.name] = True
                    test_self.assertEqual(event.results[0].get(0), 'hello')

                def __call__(self):
                    self.run_checks()

            MyEventHandler()()
            self.assertEqual(match_count['count'], 3)
            self.assertEqual(list(callbacks_called.keys()),
                             ['my-sequence-search',
                              'my-passthrough-search',
                              'my-pass-search'])

    @mock.patch.object(ycheck.engine.properties, 'APTPackageChecksBase')
    def test_yaml_def_scenarios_no_issue(self, apt_check):
        apt_check.is_installed.return_value = True
        setup_config(PLUGIN_NAME='juju')
        scenarios.YScenarioChecker()()
        self.assertEqual(IssuesManager().load_issues(), {})

    def test_yaml_def_scenario_checks_false(self):
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, DATA_ROOT=dtmp,
                         PLUGIN_NAME='myplugin')
            logfile = os.path.join(dtmp, 'foo.log')
            open(os.path.join(dtmp, 'scenarios.yaml'), 'w').write(
                                                               SCENARIO_CHECKS)
            contents = ['2021-04-01 00:31:00.000 an event\n']
            self._create_search_results(logfile, contents)
            checker = scenarios.YScenarioChecker()
            checker.load()
            self.assertEqual(len(checker.scenarios), 1)
            for scenario in checker.scenarios:
                for check in scenario.checks.values():
                    self.assertFalse(check.result)

            # now run the scenarios
            checker()

            self.assertEqual(IssuesManager().load_issues(), {})

    def test_yaml_def_scenario_checks_requires(self):
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, PLUGIN_NAME='myplugin')
            open(os.path.join(dtmp, 'scenarios.yaml'), 'w').write(
                                                               SCENARIO_CHECKS)
            checker = scenarios.YScenarioChecker()
            checker.load()
            self.assertEqual(len(checker.scenarios), 1)
            checked = 0
            for scenario in checker.scenarios:
                for check in scenario.checks.values():
                    if check.name == 'apt_pkg_exists':
                        checked += 1
                        self.assertTrue(check.result)
                    elif check.name == 'snap_pkg_exists':
                        checked += 1
                        self.assertTrue(check.result)
                    elif check.name == 'service_exists_and_enabled':
                        checked += 1
                        self.assertTrue(check.result)
                    elif check.name == 'service_exists_not_enabled':
                        checked += 1
                        self.assertFalse(check.result)

            self.assertEqual(checked, 4)

            # now run the scenarios
            checker()

            self.assertEqual(IssuesManager().load_issues(), {})

    @mock.patch('hotsos.core.ycheck.engine.properties.CLIHelper')
    def test_yaml_def_scenario_checks_expr(self, mock_cli):
        mock_cli.return_value = mock.MagicMock()
        mock_cli.return_value.date.return_value = "2021-04-03 00:00:00"
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, DATA_ROOT=dtmp,
                         PLUGIN_NAME='myplugin')
            logfile = os.path.join(dtmp, 'foo.log')
            open(os.path.join(dtmp, 'scenarios.yaml'), 'w').write(
                                                               SCENARIO_CHECKS)
            contents = ['2021-04-01 00:31:00.000 an event\n',
                        '2021-04-01 00:32:00.000 an event\n',
                        '2021-04-01 00:33:00.000 an event\n',
                        '2021-04-02 00:36:00.000 an event\n',
                        '2021-04-02 00:00:00.000 an event\n',
                        ]
            self._create_search_results(logfile, contents)
            checker = scenarios.YScenarioChecker()
            checker.load()
            self.assertEqual(len(checker.scenarios), 1)
            for scenario in checker.scenarios:
                for check in scenario.checks.values():
                    if check.name == 'logmatch':
                        self.assertTrue(check.result)

            # now run the scenarios
            checker.run()

        msg = ("log matched 5 times")
        issues = list(IssuesStore().load().values())[0]
        self.assertEqual([issue['desc'] for issue in issues], [msg])

    def _create_search_results(self, path, contents):
        with open(path, 'w') as fd:
            for line in contents:
                fd.write(line)

        s = FileSearcher()
        s.add_search_term(SearchDef(r'^(\S+) (\S+) .+', tag='all'), path)
        return s.search().find_by_tag('all')

    def test_get_datetime_from_result(self):
        result = mock.MagicMock()
        result.get.side_effect = lambda idx: _result.get(idx)

        _result = {1: '2022-01-06', 2: '12:34:56.123'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, datetime.datetime(2022, 1, 6, 12, 34, 56, 123000))

        _result = {1: '2022-01-06', 2: '12:34:56'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, datetime.datetime(2022, 1, 6, 12, 34, 56))

        _result = {1: '2022-01-06'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, datetime.datetime(2022, 1, 6, 0, 0))

        _result = {1: '2022-01-06 12:34:56.123'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, datetime.datetime(2022, 1, 6, 12, 34, 56, 123000))

        _result = {1: '2022-01-06 12:34:56'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, datetime.datetime(2022, 1, 6, 12, 34, 56))

        _result = {1: '2022-01-06'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, datetime.datetime(2022, 1, 6, 0, 0))

        _result = {1: '2022-01-06', 2: 'foo'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, datetime.datetime(2022, 1, 6, 0, 0))

        _result = {1: 'foo'}
        ts = YPropertyCheck.get_datetime_from_result(result)
        self.assertEqual(ts, None)

    @mock.patch('hotsos.core.ycheck.engine.properties.CLIHelper')
    def test_yaml_def_scenario_result_filters_by_age(self, mock_cli):
        mock_cli.return_value = mock.MagicMock()
        mock_cli.return_value.date.return_value = "2022-01-07 00:00:00"

        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, DATA_ROOT=dtmp,
                         PLUGIN_NAME='myplugin')
            logfile = os.path.join(dtmp, 'foo.log')

            contents = ['2022-01-06 00:00:00.000 an event\n']
            results = self._create_search_results(logfile, contents)

            result = YPropertyCheck.filter_by_age(results, 48)
            self.assertEqual(len(result), 1)

            result = YPropertyCheck.filter_by_age(results, 24)
            self.assertEqual(len(result), 1)

            result = YPropertyCheck.filter_by_age(results, 23)
            self.assertEqual(len(result), 0)

    def test_yaml_def_scenario_result_filters_by_period(self):
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, DATA_ROOT=dtmp,
                         PLUGIN_NAME='myplugin')
            logfile = os.path.join(dtmp, 'foo.log')

            contents = ['2021-04-01 00:01:00.000 an event\n']
            results = self._create_search_results(logfile, contents)
            result = YPropertyCheck.filter_by_period(results, 24, 1)
            self.assertEqual(len(result), 1)

            result = YPropertyCheck.filter_by_period(results, 24, 2)
            self.assertEqual(len(result), 0)

            contents = ['2021-04-01 00:01:00.000 an event\n',
                        '2021-04-01 00:02:00.000 an event\n',
                        '2021-04-03 00:01:00.000 an event\n',
                        ]
            results = self._create_search_results(logfile, contents)
            result = YPropertyCheck.filter_by_period(results, 24, 2)
            self.assertEqual(len(result), 2)

            contents = ['2021-04-01 00:00:00.000 an event\n',
                        '2021-04-01 00:01:00.000 an event\n',
                        '2021-04-01 00:02:00.000 an event\n',
                        '2021-04-02 00:00:00.000 an event\n',
                        '2021-04-02 00:01:00.000 an event\n',
                        ]
            results = self._create_search_results(logfile, contents)
            result = YPropertyCheck.filter_by_period(results, 24, 4)
            self.assertEqual(len(result), 4)

            contents = ['2021-04-01 00:00:00.000 an event\n',
                        '2021-04-01 00:01:00.000 an event\n',
                        '2021-04-02 00:01:00.000 an event\n',
                        '2021-04-02 00:02:00.000 an event\n',
                        ]
            results = self._create_search_results(logfile, contents)
            result = YPropertyCheck.filter_by_period(results, 24, 4)
            self.assertEqual(len(result), 0)

            contents = ['2021-04-01 00:00:00.000 an event\n',
                        '2021-04-01 00:01:00.000 an event\n',
                        '2021-04-02 02:00:00.000 an event\n',
                        '2021-04-03 01:00:00.000 an event\n',
                        '2021-04-04 02:00:00.000 an event\n',
                        '2021-04-05 02:00:00.000 an event\n',
                        '2021-04-06 01:00:00.000 an event\n',
                        ]
            results = self._create_search_results(logfile, contents)
            result = YPropertyCheck.filter_by_period(results, 24, 3)
            self.assertEqual(len(result), 3)

    def test_fs_override_inheritance(self):
        """
        When a directory is used to group definitions and overrides are
        provided in a <dirname>.yaml file, we need to make sure those overrides
        do not supersceded overrides of the same type used by definitions in
        the same directory.
        """
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, DATA_ROOT=dtmp,
                         PLUGIN_NAME='myplugin')
            overrides = os.path.join(dtmp, 'mytype', 'myplugin', 'mytype.yaml')
            defs = os.path.join(dtmp, 'mytype', 'myplugin', 'defs.yaml')
            os.makedirs(os.path.dirname(overrides))

            with open(overrides, 'w') as fd:
                fd.write("requires:\n")
                fd.write("  property: foo\n")

            with open(defs, 'w') as fd:
                fd.write("foo: bar\n")

            expected = {'mytype': {
                            'requires': {
                                'property': 'foo'}},
                        'defs': {'foo': 'bar'}}
            self.assertEqual(YDefsLoader('mytype').load_plugin_defs(),
                             expected)

            with open(defs, 'a') as fd:
                fd.write("requires:\n")
                fd.write("  apt: apackage\n")

            expected = {'mytype': {
                            'requires': {
                                'property': 'foo'}},
                        'defs': {
                            'foo': 'bar',
                            'requires': {
                                'apt': 'apackage'}}}
            self.assertEqual(YDefsLoader('mytype').load_plugin_defs(),
                             expected)

    @mock.patch('hotsos.core.plugins.openstack.OpenstackChecksBase')
    def test_requires_grouped(self, mock_plugin):
        mock_plugin.return_value = mock.MagicMock()
        r1 = {'property':
              'hotsos.core.plugins.openstack.OpenstackChecksBase.r1'}
        r2 = {'property':
              'hotsos.core.plugins.openstack.OpenstackChecksBase.r2'}
        r3 = {'property':
              'hotsos.core.plugins.openstack.OpenstackChecksBase.r3'}
        requires = {'requires': [{'or': [r1, r2]}]}

        mock_plugin.return_value.r1 = False
        mock_plugin.return_value.r2 = False
        group = YDefsSection('test', requires)

        results = []
        for leaf in group.leaf_sections:
            self.assertEqual(len(leaf.requires), 1)
            for _requires in leaf.requires:
                for op in _requires:
                    for item in op:
                        for rtype in item:
                            for entry in rtype:
                                results.append(entry.result)

            self.assertFalse(leaf.requires.passes)

        self.assertFalse(group.leaf_sections[0].requires.passes)
        self.assertEqual(len(results), 2)
        self.assertEqual(results, [False, False])

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = False
        group = YDefsSection('test', requires)
        self.assertTrue(group.leaf_sections[0].requires.passes)

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = True
        group = YDefsSection('test', requires)
        self.assertTrue(group.leaf_sections[0].requires.passes)

        requires = {'requires': [{'and': [r1, r2]}]}

        mock_plugin.return_value.r1 = False
        mock_plugin.return_value.r2 = False
        group = YDefsSection('test', requires)
        self.assertFalse(group.leaf_sections[0].requires.passes)

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = False
        group = YDefsSection('test', requires)
        self.assertFalse(group.leaf_sections[0].requires.passes)

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = True
        group = YDefsSection('test', requires)
        self.assertTrue(group.leaf_sections[0].requires.passes)

        requires = {'requires': [{'and': [r1, r2],
                                  'or': [r1, r2]}]}

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = False
        group = YDefsSection('test', requires)
        self.assertFalse(group.leaf_sections[0].requires.passes)

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = True
        group = YDefsSection('test', requires)
        self.assertTrue(group.leaf_sections[0].requires.passes)

        requires = {'requires': [{'and': [r1, r2],
                                  'or': [r1, r2]}]}

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = False
        group = YDefsSection('test', requires)
        self.assertFalse(group.leaf_sections[0].requires.passes)

        requires = {'requires': [r1, {'and': [r3],
                                      'or': [r1, r2]}]}

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = False
        mock_plugin.return_value.r3 = True
        group = YDefsSection('test', requires)
        self.assertTrue(group.leaf_sections[0].requires.passes)

        requires = {'requires': [{'and': [r3],
                                  'or': [r1, r2]}]}

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = False
        mock_plugin.return_value.r3 = True
        group = YDefsSection('test', requires)
        self.assertTrue(group.leaf_sections[0].requires.passes)

        # same as prev test but with dict instead list
        requires = {'requires': {'and': [r3],
                                 'or': [r1, r2]}}

        mock_plugin.return_value.r1 = True
        mock_plugin.return_value.r2 = False
        mock_plugin.return_value.r3 = True
        group = YDefsSection('test', requires)
        self.assertTrue(group.leaf_sections[0].requires.passes)

    @mock.patch('hotsos.core.ycheck.engine.properties.APTPackageChecksBase')
    def test_yaml_def_requires_apt(self, mock_apt):
        tested = 0
        expected = {'2.0': False,
                    '3.0': True,
                    '3.1': True,
                    '4.0': True,
                    '5.0': True,
                    '5.2': True,
                    '5.3': False,
                    '6.0': False}
        mock_apt.return_value = mock.MagicMock()
        mock_apt.return_value.is_installed.return_value = True
        for ver, result in expected.items():
            mock_apt.return_value.get_version.return_value = ver
            mydef = YDefsSection('mydef',
                                 yaml.safe_load(YAML_DEF_REQUIRES_APT))
            for entry in mydef.leaf_sections:
                tested += 1
                self.assertEqual(entry.requires.passes, result)

        self.assertEqual(tested, len(expected))

    def test_yaml_def_requires_systemd_pass(self):
        mydef = YDefsSection('mydef',
                             yaml.safe_load(YAML_DEF_REQUIRES_SYSTEMD_PASS_1))
        for entry in mydef.leaf_sections:
            self.assertTrue(entry.requires.passes)

    def test_yaml_def_requires_systemd_fail(self):
        mydef = YDefsSection('mydef',
                             yaml.safe_load(YAML_DEF_REQUIRES_SYSTEMD_FAIL_1))
        for entry in mydef.leaf_sections:
            self.assertFalse(entry.requires.passes)

        mydef = YDefsSection('mydef',
                             yaml.safe_load(YAML_DEF_REQUIRES_SYSTEMD_FAIL_2))
        for entry in mydef.leaf_sections:
            self.assertFalse(entry.requires.passes)

    def test_yaml_def_requires_systemd_started_after_pass(self):
        current = datetime.datetime.now()
        with mock.patch('hotsos.core.host_helpers.systemd.SystemdService',
                        FakeServiceObjectManager({
                            'neutron-openvswitch-agent':
                                current,
                            'openvswitch-switch':
                                current + datetime.timedelta(seconds=120)})):
            content = yaml.safe_load(YAML_DEF_REQUIRES_SYSTEMD_STARTED_AFTER)
            mydef = YDefsSection('mydef', content)
            for entry in mydef.leaf_sections:
                self.assertTrue(entry.requires.passes)

    def test_yaml_def_requires_systemd_started_after_fail(self):
        current = datetime.datetime.now()
        with mock.patch('hotsos.core.host_helpers.systemd.SystemdService',
                        FakeServiceObjectManager({'neutron-openvswitch-agent':
                                                  current,
                                                  'openvswitch-switch':
                                                  current})):
            content = yaml.safe_load(YAML_DEF_REQUIRES_SYSTEMD_STARTED_AFTER)
            mydef = YDefsSection('mydef', content)
            for entry in mydef.leaf_sections:
                self.assertFalse(entry.requires.passes)

        with mock.patch('hotsos.core.host_helpers.systemd.SystemdService',
                        FakeServiceObjectManager({
                            'neutron-openvswitch-agent': current,
                            'openvswitch-switch':
                                current + datetime.timedelta(seconds=119)})):
            content = yaml.safe_load(YAML_DEF_REQUIRES_SYSTEMD_STARTED_AFTER)
            mydef = YDefsSection('mydef', content)
            for entry in mydef.leaf_sections:
                self.assertFalse(entry.requires.passes)

    def test_yaml_def_nested_logic(self):
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, DATA_ROOT=dtmp)
            plugin_dir = os.path.join(dtmp, 'scenarios',
                                      HotSOSConfig.PLUGIN_NAME)
            os.makedirs(plugin_dir)
            open(os.path.join(plugin_dir, 'scenarios.yaml'),
                 'w').write(YDEF_NESTED_LOGIC)
            scenarios.YScenarioChecker()()
            issues = list(IssuesStore().load().values())[0]
            self.assertEqual(sorted([issue['desc'] for issue in issues]),
                             sorted(['conc1', 'conc3']))

    def test_yaml_def_mapped_overrides(self):
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, PLUGIN_NAME='myplugin')
            open(os.path.join(dtmp, 'scenarios.yaml'), 'w').write(
                                                      YAML_DEF_REQUIRES_MAPPED)
            checker = scenarios.YScenarioChecker()
            checker.load()
            self.assertEqual(len(checker.scenarios), 1)
            for scenario in checker.scenarios:
                self.assertEqual(len(scenario.checks), 2)
                for check in scenario.checks.values():
                    self.assertTrue(check.result)

    def test_failed_scenario_caught(self):
        with tempfile.TemporaryDirectory() as dtmp:
            setup_config(PLUGIN_YAML_DEFS=dtmp, PLUGIN_NAME='myplugin')
            open(os.path.join(dtmp, 'scenarios.yaml'), 'w').write(
                                                      SCENARIO_W_ERROR)
            scenarios.YScenarioChecker()()
            issues = list(IssuesStore().load().values())
            self.assertEqual(len(issues[0]), 2)
            i_types = [i['type'] for i in issues[0]]
            self.assertEqual(sorted(i_types),
                             sorted(['SystemWarning',
                                     'HotSOSScenariosWarning']))
            for issue in issues[0]:
                if issue['type'] == 'HotSOSScenariosWarning':
                    msg = ("One or more scenarios failed to run (scenarioB) - "
                           "run hotsos in debug mode (--debug) to get more "
                           "detail")
                    self.assertEqual(issue['desc'], msg)