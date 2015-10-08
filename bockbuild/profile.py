import os
from optparse import OptionParser
from util.util import *
from util.csproj import *
from environment import Environment
from bockbuild.package import *
import collections
import hashlib
import sys
import traceback


class Profile:
	def __init__ (self, root = None, prefix = False):		
		self.build_root = os.path.join (self.root, 'build-root')
		self.staged_prefix = os.path.join (self.root, 'stage-root')
		self.package_root = os.path.join (self.root, 'package-root')
		self.prefix = prefix if prefix else os.path.join (self.root, 'install-root')
                self.source_cache = os.getenv('BOCKBUILD_SOURCE_CACHE') or os.path.realpath (os.path.join (self.root, 'cache'))
                self.cpu_count = get_cpu_count ()
		self.host = get_host ()
		self.uname = backtick ('uname -a')

		
		self.env.set ('BUILD_PREFIX', '%{prefix}')
		self.env.set ('BUILD_ARCH', '%{arch}')
		self.env.set ('BOCKBUILD_ENV', '1')

		self.profile_name = self.__class__.__name__

		self.parse_options ()
		
		Package.profile = self

	def parse_options (self):
		self.default_run_phases = ['prep', 'build', 'install']
		parser = OptionParser (usage = 'usage: %prog [options] [package_names...]')
		parser.add_option ('-b', '--build',
			action = 'store_true', dest = 'do_build', default = False,
			help = 'build the profile')
		parser.add_option ('-P', '--package',
			action = 'store_true', dest = 'do_package', default = False,
			help = 'package the profile')
		parser.add_option ('-z', '--bundle',
			action = 'store_true', dest = 'do_bundle', default = False,
			help = 'create a distributable bundle from a build')
		parser.add_option ('-o', '--output-dir',
			default = None, action = 'store', dest = 'output_dir',
			help = 'output directory for housing the bundle (--bundle|-z)')
		parser.add_option ('-k', '--skeleton-dir',
			default = None, action = 'store',  dest = 'skeleton_dir',
			help = 'skeleton directory containing misc files to copy into bundle (--bundle|-z)')
		parser.add_option ('-v', '--verbose',
			action = 'store_true', dest = 'verbose', default = False,
			help = 'show all build output (e.g. configure, make)')
		parser.add_option ('-i', '--include-phase',
			action = 'append', dest = 'include_run_phases', default = [],
			help = 'explicitly include a build phase to run %s' % self.default_run_phases)
		parser.add_option ('-x', '--exclude-phase',
			action = 'append', dest = 'exclude_run_phases', default = [],
			help = 'explicitly exclude a build phase from running %s' % self.default_run_phases)
		parser.add_option ('-s', '--only-sources',
			action = 'store_true', dest = 'only_sources', default = False,
			help = 'only fetch sources, do not run any build phases')
		parser.add_option ('-d', '--debug', default = False,
			action = 'store_true', dest = 'debug',
			help = 'Build with debug flags enabled')
		parser.add_option ('-e', '--environment', default = False,
			action = 'store_true', dest = 'dump_environment',
			help = 'Dump the profile environment as a shell-sourceable list of exports ')
		parser.add_option ('-r', '--release', default = False,
			action = 'store_true', dest = 'release_build',
			help = 'Whether or not this build is a release build')
		parser.add_option ('', '--csproj-env', default = False,
			action = 'store_true', dest = 'dump_environment_csproj',
			help = 'Dump the profile environment xml formarted for use in .csproj files')
		parser.add_option ('', '--csproj-insert', default = None,
			action = 'store', dest = 'csproj_file',
			help = 'Inserts the profile environment variables into VS/MonoDevelop .csproj files')
		parser.add_option ('', '--arch', default = 'default',
			action = 'store', dest = 'arch',
			help = 'Select the target architecture(s) for the package')
		parser.add_option ('', '--shell', default = False,
			action = 'store_true', dest = 'shell',
			help = 'Get an shell with the package environment')
		parser.add_option ('', '--unsafe', default = False,
			action = 'store_true', dest = 'unsafe',
			help = 'Prevents full rebuilds when a build environment change is detected. Useful for debugging.')

		self.parser = parser		

	def build (self):

		Profile.setup (self)
		self.setup ()

		self.full_rebuild = self.track_env ()

		if self.full_rebuild:
			warn ('Build environment changed')
			for d in os.listdir (self.build_root):
				if d.endswith ('.cache') or d.endswith ('.artifact'):
					os.remove (os.path.join(self.build_root, d))


		if self.cmd_options.shell:
			title ('Shell')
			self.shell ()

		if self.cmd_options.do_build:
			ensure_dir (self.staged_prefix, True)

			title ('Building release')
			for package in self.release_packages.values ():
				package.start_build (self.staged_prefix, self.prefix)

		if self.cmd_options.do_bundle:
			if not self.cmd_options.output_dir == None:
				self.bundle_output_dir = os.path.join (os.getcwd (), 'bundle')
			if not self.cmd_options.skeleton_dir == None:
				self.bundle_skeleton_dir = os.path.join (os.getcwd (), 'skeleton')
			self.bundle ()
			return

		if self.cmd_options.do_package:
			title ('Packaging')
			protect_dir (self.staged_prefix)
			ensure_dir (self.package_root, True)

			run_shell('rsync -aPq %s/* %s' % (self.staged_prefix, self.package_root), False)
			unprotect_dir (self.package_root)

			self.process_release (self.package_root)
			self.package ()

	def track_env (self):
		tracked_env = []

		if self.unsafe:
			warn ('Running with --unsafe, build environment not checked for changes')

		self.env.compile ()
		self.env.export ()
		tracked_env.extend (self.env.serialize ())

		changed = False if self.unsafe else update (tracked_env, os.path.join (self.root, 'global.env'), show_diff = True)

		self.envfile = os.path.join (self.root, self.profile_name) + '_env.sh'
		self.env.dump (self.envfile)
		os.chmod (self.envfile, 0755)

		return changed

	def setup (self):
		progress ('Setting up packages')

		self.cmd_options, self.cmd_args = self.parser.parse_args ()

		exp_list = None
		if '->' in self.cmd_args: # "... [package name]" will include all packages up to package name
			assert len (self.cmd_args) == 2
			found = False
			exp_list = list()
			for source in self.packages:
				exp_list.append (source)
				if source == self.cmd_args[1]:
					found = True
					break
			assert found

		self.packages_to_build = exp_list or self.cmd_args or self.packages

		info ('packages: ' + str(self.packages_to_build))

		self.verbose = self.cmd_options.verbose
		self.run_phases = self.default_run_phases
		self.arch = self.cmd_options.arch
		self.unsafe = self.cmd_options.unsafe

		ensure_dir (self.source_cache, False)
		ensure_dir (self.build_root, False)

		self.release_packages = collections.OrderedDict()

		for source in self.packages_to_build:
			package = self.load_package (source, self.build_root, self.resource_root)
			trace (package)
			self.release_packages[package.name] = package

	def load_package (self, source, build_root, resource_root):
		if isinstance (source, Package): # package can already be loaded in the source list
			return source

		if not os.path.isabs (source):
			fullpath = os.path.join (resource_root, source + '.py')
		else:
			fullpath = source

		if not os.path.exists (fullpath):
			error ("Resource '%s' not found" % source)

		Package.last_instance = None

		execfile (fullpath, globals())

		if Package.last_instance == None:
			error ('%s does not provide a valid package.' % source)

		new_package = Package.last_instance
		new_package._path = fullpath

		new_package.setup (build_root, resource_root)

		if is_newer (fullpath, new_package.build_artifact):
			new_package.mark_updated ('Manifest: %s' % source)

		return new_package

	class FileProcessor (object):
		def __init__ (self, harness = None, match = None, process = None,  extra_files = None):
			self.harness = harness
			self.match = match
			self.files = list (extra_files) if extra_files else list ()
			self.root = None

		def relpath (self, path):
			return os.path.relpath (path, self.root)

		def run (self):
			for path in self.files:
				self.harness (path, self.process)
		def end (self):
			return


	def postprocess (self, processors, directory, filefilter = None):
		def simple_harness (path, func):
			if not os.path.lexists (path):
				return # file removed by previous processor function
			# TODO: Fix so that it works on symlinks
			# hash = hashlib.sha1(open(path).read()).hexdigest()
			func (path)
			if not os.path.lexists (path):
				trace ('Removed file: %s' % path)
			#if hash != hashlib.sha1(open(path).read()).hexdigest():
			#	warn ('Changed file: %s' % path)

		for proc in processors:
			proc.root = directory
			if proc.harness == None:
				proc.harness = simple_harness
			if proc.match == None:
					error ('proc %s has no match function' % proc.__class__.__name__)

		for path in filter (filefilter, iterate_dir (directory, with_dirs = True, with_links = True)):
			filetype = get_filetype (path)
			for proc in processors:
				if proc.match (path, filetype) == True:
					trace ('%s  matched %s / %s' % (proc.__class__.__name__, os.path.basename(path), filetype) )
					proc.files.append (path)

		for proc in processors:
			trace ('%s: %s items' % (proc.__class__.__name__ , len (proc.files)))
			proc.run ()


		for proc in processors:
			proc.end ()
			proc.harness = None
			proc.files = []

import importlib

class Bockbuild:
	def __init__ (self, root):
		self.name = 'bockbuild'
		self.root = root
		self.env = Environment (self)
		find_git (self)
		self.env.set ('bockbuild_revision', git_get_revision(self))
		Profile.env = self.env

		loginit ('bockbuild rev. %s %s' % (self.env.bockbuild_revision, "" or "(branch: %s)" % git_get_branch(self)))
		info ('cmd: %s' % ' '.join(sys.argv))

	def run (self, profile, work_dir):
		while True:
			try:
				self.profile_name = profile.__name__
				info ('profile: %s' % self.profile_name)
				self.profile = profile ()
				self.profile.root = work_dir
				self.profile.resource_root = os.path.join (self.root, 'packages')
				self.profile.build ()
			except Exception as e:
			        exc_type, exc_value, exc_traceback = sys.exc_info()
			        error ('%s (%s)' % (e ,exc_type.__name__), more_output = True)
			        error ('\n'.join (('%s:%s @%s\n\t...%s\n' % p for p in traceback.extract_tb(exc_traceback)[-3:])), more_output = True)

			raw_input("Press Enter to update...")
			# reload ('bockbuild.profile')

