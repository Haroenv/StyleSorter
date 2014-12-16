import sublime
import sublime_plugin
from StyleSorter.Parser import Parser
from time import sleep


class SortCommand(sublime_plugin.TextCommand):

	NAME = 'StyleSorter'

	def run(self, edit):
		settings = sublime.load_settings(SortCommand.NAME + '.sublime-settings')
		ordering = settings.get('ordering')

		self.view.set_status(SortCommand.NAME, 'Parsing stylesheet')
		region = sublime.Region(0, self.view.size())
		text = self.view.substr(region)
		thread = Parser(text, ordering)
		thread.start()
		self.handleThread(thread, edit, region)

	def handleThread(self, thread, edit, region):
		while thread.isAlive():
			sleep(0.0001)
		self.updateFile(thread.result, edit, region)

	def updateFile(self, formatted, edit, region):
		self.view.set_status(SortCommand.NAME, 'Updating stylesheet')
		self.view.replace(edit, region, formatted)
		self.view.erase_status(SortCommand.NAME)
		sublime.status_message(SortCommand.NAME + ' successfully sorted your stylesheet.')

	def description(self):
		return 'Super CSS sorter.'
