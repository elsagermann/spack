# Copyright 2013-2020 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os

import llnl.util.filesystem as fs
import llnl.util.tty as tty

from spack import *


class Libxml2(AutotoolsPackage):
    """Libxml2 is the XML C parser and toolkit developed for the Gnome
       project (but usable outside of the Gnome platform), it is free
       software available under the MIT License."""

    homepage = "http://xmlsoft.org"
    url      = "http://xmlsoft.org/sources/libxml2-2.9.8.tar.gz"

    version('2.9.10', sha256='aafee193ffb8fe0c82d4afef6ef91972cbaf5feea100edc2f262750611b4be1f')
    version('2.9.9',  sha256='94fb70890143e3c6549f265cee93ec064c80a84c42ad0f23e85ee1fd6540a871')
    version('2.9.8',  sha256='0b74e51595654f958148759cfef0993114ddccccbb6f31aee018f3558e8e2732')
    version('2.9.4',  sha256='ffb911191e509b966deb55de705387f14156e1a56b21824357cdf0053233633c')
    version('2.9.2',  sha256='5178c30b151d044aefb1b08bf54c3003a0ac55c59c866763997529d60770d5bc')
    version('2.7.8',  sha256='cda23bc9ebd26474ca8f3d67e7d1c4a1f1e7106364b690d822e009fdc3c417ec')

    variant('python', default=False, description='Enable Python support')

    depends_on('pkgconfig@0.9.0:', type='build')
    depends_on('iconv')
    depends_on('zlib')
    depends_on('xz')

    # avoid cycle dependency for concretizer
    depends_on('python+shared~libxml2', when='+python')
    extends('python', when='+python',
            ignore=r'(bin.*$)|(include.*$)|(share.*$)|(lib/libxml2.*$)|'
            '(lib/xml2.*$)|(lib/cmake.*$)')

    # XML Conformance Test Suites
    # See http://www.w3.org/XML/Test/ for information
    resource(name='xmlts', url='https://www.w3.org/XML/Test/xmlts20080827.tar.gz',
             sha256='96151685cec997e1f9f3387e3626d61e6284d4d6e66e0e440c209286c03e9cc7')

    @property
    def headers(self):
        include_dir = self.spec.prefix.include.libxml2
        hl = find_all_headers(include_dir)
        hl.directories = include_dir
        return hl

    def configure_args(self):
        spec = self.spec

        args = ['--with-lzma={0}'.format(spec['xz'].prefix),
                '--with-iconv={0}'.format(spec['iconv'].prefix)]

        if '+python' in spec:
            args.extend([
                '--with-python={0}'.format(spec['python'].home),
                '--with-python-install-dir={0}'.format(site_packages_dir)
            ])
        else:
            args.append('--without-python')

        return args

    @run_after('install')
    @on_package_attributes(run_tests=True)
    def import_module_test(self):
        if '+python' in self.spec:
            with working_dir('spack-test', create=True):
                python('-c', 'import libxml2')

    def _run_test(self, exe, options, expected, status):
        """Run the test and confirm obtain the expected results

        Args:
            exe (str): the name of the executable
            options (list of str): list of options to pass to the runner
            expected (list of str): list of expected output strings
            status (int or None): the expected process status if int or None
                if the test is expected to succeed
        """
        result = 'fail with status {0}'.format(status) if status else 'succeed'
        tty.msg('test: {0}: expect to {1}'.format(exe, result))
        runner = which(exe)
        assert runner is not None

        try:
            output = runner(*options, output=str.split, error=str.split)
            assert not status, 'Expected execution to fail'
        except ProcessError as err:
            output = str(err)
            status_msg = 'exited with status {0}'.format(status)
            expected_msg = 'Expected \'{0}\' in \'{1}\''.format(
                status_msg, err.message)
            assert status_msg in output, expected_msg

        for check in expected:
            assert check in output

    def test(self):
        """Perform smoke tests on the installed package"""
        # Start with what we already have post-install
        tty.msg('test: Performing simple import test')
        self.import_module_test()

        # Now run defined tests based on expected executables
        dtd_path = './data/info.dtd'
        test_fn = 'test.xml'
        exec_checks = {
            'xml2-config': [
                (['--version'], [str(self.spec.version)], None)],
            'xmllint': [
                (['--version'],
                 ['using libxml', str(self.spec.version).replace('.', '0')],
                 None),
                (['--auto', '-o', test_fn], [], None),
                (['--postvalid', test_fn],
                 ['validity error', 'no DTD found', 'does not validate'], 3),
                (['--dtdvalid', dtd_path, test_fn],
                 ['validity error', 'does not follow the DTD'], 3),
                (['--dtdvalid', dtd_path, './data/info.xml'], [], None)],
            'xmlcatalog': [
                (['--create'], ['<catalog xmlns', 'catalog"/>'], None)],
        }
        for exe in exec_checks:
            for options, expected, status in exec_checks[exe]:
                self._run_test(exe, options, expected, status)

        # Perform some cleanup
        fs.force_remove(test_fn)
