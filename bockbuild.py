#!/usr/bin/python -u -OO

import sys

Sources = set ()

if __name__ == "__main__":
	print sys.modules

class Source:
	def __init__ (self, name, url, sources = [], friendly_name = None):
		for source in sources:
			Source.register (source)
		self.sources = sources
		self.dependents = []



	def refresh (self):
		raise BockbuildError ('')

	def pre_resolve (self):
		trace ('Resolving')


class Sources (Set):
	def register (self, name):
		pass
	def reference (self, name):
		pass
	def target (self, name): # target ('fulldist','artifact')
		pass



class File (Source):
	def init (self):
		self.path = None
	def resolve (self):
		if not os.path.exists (path):
			raise SourceException ('%s does not exist.')

class ResourceFile (Source):
	def setup (self):
		self.sources = [ ]

class Distribution (Source):
	def add (self, url, )

class Compost (Source):



class Bockbuild(Source):
	def update (self, )

	def __init__ (self, root):
		#


		Source.__init__ 
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

	def register_target ()

