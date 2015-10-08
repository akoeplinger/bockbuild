from profile import Profile
import os

class UnixProfile (Profile):
	def __init__ (self, prefix = False):
		Profile.__init__ (self, prefix)
		self.toolchain_root = os.path.join (self.root, 'toolchain-root')
		self.name = 'unix'

		self.gcc_flags = ['-I%s/include' % self.staged_prefix]
		self.ld_flags = ['-L%s/lib' % self.staged_prefix]

		self.env.set ('PATH', ':',
			'%{toolchain_root}/bin',
			'%{staged_prefix}/bin',
			'/usr/bin',
			'/bin',
			'/usr/local/git/bin')

		self.env.set ('C_INCLUDE_PATH',  '%{staged_prefix}/include')

		#self.env.set ('LD_LIBRARY_PATH', '%{staged_prefix}/lib')

		self.env.set ('ACLOCAL_FLAGS',   '-I%{staged_prefix}/share/aclocal')
		self.env.set ('PKG_CONFIG_PATH', ':',
			'%{staged_prefix}/lib/pkgconfig',
			'%{staged_prefix}/share/pkgconfig',
			'%{toolchain_root}/lib/pkgconfig',
			'%{toolchain_root}/share/pkgconfig')

		self.env.set ('XDG_CONFIG_DIRS', '%{staged_prefix}/etc/xdg')
		self.env.set ('XDG_DATA_DIRS',   '%{staged_prefix}/share')
		self.env.set ('XDG_CONFIG_HOME', '$HOME/.config')
