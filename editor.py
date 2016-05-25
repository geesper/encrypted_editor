#!/usr/bin/python

# http://www.objgen.com/json/models/Avn

import json
import yaml
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random

import os
from StringIO import StringIO
import operator
import ast

load_file = 'encrypted_file.txt'
password = "password"

class MyWindow(Gtk.Window):
   def __init__(self):
      Gtk.Window.__init__(self, title="Encrypted Notebook")
      password_prompt(self, "Please enter your password to unlock.", "Password")
      self.grid = Gtk.Grid()
      # Load in data:
      self.load_data_from_file(load_file)
      self.create_password_area()
      self.create_side_bar()
      self.create_notes_area()
      self.create_save_cancel()
      self.create_right_click_menu()
      self.add(self.grid)

      css = Gtk.CssProvider()
      css.load_from_path('style.css')
      screen = Gdk.Screen.get_default()
      style = Gtk.StyleContext()
      style.add_provider_for_screen(screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

      # Used for the clipboard:
      self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
      self.clipboard_mouse = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)

      # Initial variables set
      self.current_item = None
      self.sidebar_current_selection = 0
      self.sidebar_locked = False

      # Set keyboard shortcuts
      shortcuts = Gtk.AccelGroup()
      self.add_accel_group(shortcuts)
      # Control S for saving
      key, mod = Gtk.accelerator_parse('<Control>s')
      self.save_button.add_accelerator('activate', shortcuts, key, mod, Gtk.AccelFlags.VISIBLE)

      # Escape for cancel
      key, mod = Gtk.accelerator_parse('Escape')
      self.cancel_button.add_accelerator('activate', shortcuts, key, mod, Gtk.AccelFlags.VISIBLE)

      # Control N for New Note
      key, mod = Gtk.accelerator_parse('<Control>n')
      self.add_new_entry_selection.add_accelerator('activate', shortcuts, key, mod, Gtk.AccelFlags.VISIBLE)
      #self.add_new_entry_selection.connect("button_release_event", self.add_entry)


   # This ensures that the areas we want hidden at startup are not showing.
   def startup(self):
       win.show_all()
       self.save_cancel_area.hide()
       self.password_area.hide()

   def create_save_cancel(self):
       self.save_cancel_area = Gtk.Grid()
       self.save_button = Gtk.Button(label="Save")
       self.cancel_button = Gtk.Button(label="Cancel")
       self.save_button.connect("clicked", self.save_button_clicked)
       self.cancel_button.connect("clicked", self.cancel_button_clicked)
       self.save_cancel_area.add(self.save_button)
       self.save_cancel_area.attach_next_to(self.cancel_button, self.save_button, Gtk.PositionType.RIGHT, 1, 1)
       self.grid.attach_next_to(self.save_cancel_area, self.scrolledwindow, Gtk.PositionType.BOTTOM, 1,1)
       self.save_cancel_area.do_unmap(self.save_cancel_area)


   def create_password_area(self):
       username_label = Gtk.Label(label="User name")
       self.username_text = Gtk.Entry()
       self.username_text.connect("changed", self.edit_changed)
       password_label = Gtk.Label(label="Password")
       self.password_text = Gtk.Entry()
       self.password_text.set_visibility(False)
       self.password_text.connect("copy-clipboard", self.copy_password)
       self.password_text.connect("changed", self.edit_changed)
       show_password = Gtk.CheckButton("show")
       show_password.connect("toggled", self.show_password)
       show_password.set_active(False)
       self.password_area = Gtk.Grid()
       #self.password_area.set_name("password_area")
       self.password_area.add(username_label)
       self.password_area.attach_next_to(self.username_text, username_label, Gtk.PositionType.RIGHT, 1, 1)
       self.password_area.attach_next_to(password_label, username_label, Gtk.PositionType.BOTTOM, 1, 1)
       self.password_area.attach_next_to(self.password_text, password_label, Gtk.PositionType.RIGHT, 1, 1)
       self.password_area.attach_next_to(show_password, self.password_text, Gtk.PositionType.RIGHT, 1, 1)
       self.grid.attach(self.password_area, 1, 0, 1, 1)

   def create_side_bar(self):
       self.listmodel = Gtk.ListStore(str, str)
       #self.listmodel.append(["Add New Entry", "Add New Entry"])
       for entry in self.data['encrypted_item']:
          self.listmodel.append([entry['name'], str(entry['id'])])
       self.side_bar_box = Gtk.TreeView.new_with_model(self.listmodel)


       # Setting up side_bar function for when text is edited:
       renderer = Gtk.CellRendererText()
       renderer.set_property("editable", True)
       renderer.connect("edited", self.side_bar_edited)

       # Setting sorting and title name:
       column = Gtk.TreeViewColumn("List", renderer, text=0)
       column.set_sort_column_id(0)
       column.set_resizable(True)

       # Setting up a side_bar function to control when the selection can change:
       self.side_bar_box.append_column(column)
       selection_set = self.side_bar_box.get_selection()
       selection_set.set_select_function(self.allow_selection_change, None)

       # Set up a side_bar function for when the selection is allowed to change:
       self.row_activation_id = self.side_bar_box.connect("row-activated", self.side_bar_button_clicked)

       # Side_bar function for when a right click happens:
       self.side_bar_box.connect("button_release_event", self.side_bar_button_right_clicked)

       self.side_bar_box.set_activate_on_single_click(True)
       self.grid.attach(self.side_bar_box, 0, 0, 1,2)

   def create_notes_area(self):
       self.scrolledwindow = Gtk.ScrolledWindow()
       self.scrolledwindow.set_hexpand(True)
       self.scrolledwindow.set_vexpand(True)
       self.grid.attach(self.scrolledwindow, 1, 1, 1, 1)
       self.textview = Gtk.TextView()
       self.textview.set_name("editor")
       self.textbuffer = self.textview.get_buffer()
       self.textbuffer.connect("changed", self.edit_changed)
       self.scrolledwindow.add(self.textview)
       self.textview.set_editable(False)

   def create_right_click_menu(self):
      self.right_click_menu = Gtk.Menu()
      add_password = Gtk.MenuItem("Add Password")
      add_password.connect("button_release_event", self.add_password)
      self.add_new_entry_selection = Gtk.MenuItem("Add New Entry")
      self.add_new_entry_selection.connect("activate", self.add_entry)
      delete_entry = Gtk.MenuItem("Delete Entry")
      delete_entry.connect("button_release_event", self.delete_entry)
      self.right_click_menu.append(add_password)
      self.right_click_menu.append(self.add_new_entry_selection)
      self.right_click_menu.append(delete_entry)
      self.right_click_menu.show_all()


   def delete_entry(self, widget, value):
      self.right_click_menu.hide()
      delete_confirmation = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.YES_NO, "Are you sure you wish to delete this entry?\n\n%s" %(self.current_item['name']))
      response = delete_confirmation.run()
      if response == Gtk.ResponseType.YES:
         path = Gtk.TreePath(self.sidebar_current_selection)
         treeiter = self.listmodel.get_iter(path)
         label_name = self.listmodel.get_value(treeiter, 0)
         label_value = self.listmodel.get_value(treeiter, 1)
         found = False
         for item in self.data['encrypted_item']:
            if str(item['id']) == label_value:
               print(str(item))
               self.data['encrypted_item'].remove(item)
         self.listmodel.remove(treeiter)
         self.encrypt(json.dumps(self.data), load_file, password)
      else:   
         print("Not deleting!") 
      delete_confirmation.destroy()

   def add_entry(self, widget, value=None):
      self.listmodel.append(["New Entry", "none"])
      self.current_item = "Adding New Entry"
      self.populate_fields()
      self.show_save()
      self.sidebar_current_selection = len(self.listmodel) - 1
      self.sidebar_locked = False # Included to force selection to change to the "New entry" on the sidebar
      self.sidebar_select_number(self.sidebar_current_selection)
      self.sidebar_locked = True

   # This is called to determine if the edit box was changed.
   def edit_changed(self, widget):
       if self.needs_saving() == True:
           self.show_save()
           self.sidebar_locked = True
       else:
           self.hide_save()
           self.sidebar_locked = False


   def show_save(self):
       self.save_cancel_area.show()

   def hide_save(self):
       self.save_cancel_area.hide()

   # Called by the right click menu, makes sure the username/password area is visible.
   def add_password(self, widget, value):
      self.password_area.show()

   # If the side_bar is right clicked, we move the selection back to where it should be.
   def side_bar_button_right_clicked(self, value1, value2):
       if value2.button == 3:
          if self.sidebar_current_selection != None:
             self.sidebar_select_number(self.sidebar_current_selection)
             tree_sel = self.side_bar_box.get_selection()
             (name, stuff) = tree_sel.get_selected()
             self.right_click_menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

   # This handles a side_bar left click
   def side_bar_button_clicked(self, value1, value2, value3):
       self.textview.set_editable(True)
       if self.needs_saving() == True:
           self.sidebar_locked = True
       if self.sidebar_locked == False:
          self.side_bar_box.handler_unblock(self.row_activation_id)
          path = Gtk.TreePath(value2)
          treeiter = self.listmodel.get_iter(path)
          label_name = self.listmodel.get_value(treeiter, 0)
          label_value = self.listmodel.get_value(treeiter, 1)
          if label_value == "Add New Entry":
              self.listmodel.append(["New Entry", "none"])
              self.current_item = "Adding New Entry"
              self.populate_fields()
              self.show_save()
              self.sidebar_current_selection = len(self.listmodel) - 1
              self.sidebar_locked = False # Included to force selection to change to the "New entry" on the sidebar
              self.sidebar_select_number(self.sidebar_current_selection)
              self.sidebar_locked = True
          else:
             for value in self.data['encrypted_item']:
                if str(value['id']) == label_value:
                   self.current_item = value
             self.populate_fields()
             self.sidebar_current_selection = value2

   # This is used to make sure the side_bar selection cannot be changed if a save/cancel is pending.
   def allow_selection_change(self, value1, value2, value3, value4, value5):
      if self.sidebar_locked == True:
          return False
      else:
         return True

   # This is used to move the selection manually to a designated number:
   def sidebar_select_number(self, number):
       path = Gtk.TreePath(number)
       select = self.side_bar_box.get_selection()
       select.select_path(path)

   # If someone renames an entry, but then hits cancel, this reverts the name back:
   def sidebar_reset_edit(self):
       if hasattr(self, 'sidebar_reset_name') and self.sidebar_reset_name != None:
           path = Gtk.TreePath(self.sidebar_current_selection)
           treeiter = self.listmodel.get_iter(path)
           self.listmodel.set_value(treeiter, 0, self.sidebar_reset_name)
           self.current_item['name'] = self.sidebar_reset_name
           self.sidebar_reset_name = None

   # Handles hitting control-c on the password field:
   def copy_password(self, thing):
       self.clipboard.set_text(self.password_text.get_text(), -1)
       self.clipboard_mouse.set_text(self.password_text.get_text(), -1)

   # This will display/unhide the text in the password field.
   def show_password(self, button):
        value = button.get_active()
        self.password_text.set_visibility(value)

   # Reads from the current_item selected and puts the data into the appropriate fields
   def populate_fields(self):
       if self.current_item == None or self.current_item == "Adding New Entry":
          self.username_text.set_text('')
          self.password_text.set_text('')
          self.textbuffer.set_text('')
       else:
          self.username_text.set_text(self.current_item['login']['username'])
          self.password_text.set_text(self.current_item['login']['password'])
          self.textbuffer.set_text(self.current_item['text'], -1)
       if self.username_text.get_text() == '' and self.password_text.get_text() == '':
          self.password_area.hide()
       else:
          self.password_area.show()


   # Loads the data from the encrypted file.
   def load_data_from_file(self, file_name):
       if not os.path.isfile(file_name):
          print("Could not find file, so setting up the example...")
          content = open('encrypted_file_example.txt')
          print("Going to encrypt example using: %s" %(password))
          self.encrypt(content.read(), file_name, password)
       encrypted_file = self.decrypt(file_name, password)
       try:
          self.data = yaml.safe_load(StringIO(encrypted_file))
       except Exception:
          self.error("Unable to read data from file. Please check your password and try again.")
          quit()


   # This handles if an entry is renamed:
   def side_bar_edited(self, widget, path, text):
      self.listmodel[path][0] = text
      self.sidebar_reset_name = self.current_item['name']
      self.current_item['name'] = text
      self.sidebar_locked = True
      self.show_save()

   def needs_saving(self):
       if self.textview.get_editable == False:
           return False
       if self.current_item == None:
           if self.username_text.get_text() != '':
               return True
           if self.password_text.get_text() != '':
               return True
           if self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False) != '':
               return True
           #return True
       elif self.current_item == "Adding New Entry": # Adding new entry always needs to be saved (or canceled)
           return True
       else:
          if self.current_item['login']['username'] != self.username_text.get_text():
             return True
          if self.current_item['login']['password'] != self.password_text.get_text():
             return True
          if self.current_item['text'] != self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False):
             return True
       return False



   def save_button_clicked(self, widget):
       self.sidebar_locked = False
       self.sidebar_reset_name = None
       if self.current_item == "Adding New Entry":
           if self.sidebar_current_selection != None:
              new_item = {}
              path = Gtk.TreePath(self.sidebar_current_selection)
              treeiter = self.listmodel.get_iter(path)
              label_name = self.listmodel.get_value(treeiter, 0)
              new_item["name"] = label_name
              new_item["id"] = self.get_next_id_number()
              new_item["text"] = str(self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False))
              new_item["login"] = {}
              new_item["login"]["username"] = self.username_text.get_text()
              new_item["login"]["password"] = self.password_text.get_text()
              self.listmodel.append([new_item['name'], str(new_item['id'])])
              self.data['encrypted_item'].append(new_item)
              for value in self.data['encrypted_item']:
                 if value['id'] == new_item['id']:
                    self.current_item = value
              self.populate_fields()
              self.sidebar_current_selection = len(self.listmodel) - 1
              self.sidebar_select_number(self.sidebar_current_selection)
              for value in self.data['encrypted_item']:
                 if str(value['id']) == new_item['id']:
                    self.current_item = value
              self.remove_bad_sidebar_entries()
       if not self.current_item == None:
          self.current_item['login']['username'] = self.username_text.get_text()
          self.current_item['login']['password'] = self.password_text.get_text()
          self.current_item["text"] = self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False)
       self.encrypt(json.dumps(self.data), load_file, password)
       self.hide_save()
       #yeah = open('junk.txt','w')
       #yeah.write(str(self.data))
       #yeah.close()


   def cancel_button_clicked(self, widget):
       self.sidebar_locked = False
       if self.current_item == "Adding New Entry":
           self.username_text.set_text('')
           self.password_text.set_text('')
           self.textbuffer.set_text('')
           self.sidebar_current_selection = None
           self.password_area.hide()
           self.current_item = None
           self.remove_bad_sidebar_entries()
           deselect = self.side_bar_box.get_selection()
       else:
          self.username_text.set_text(self.current_item['login']['username'])
          self.password_text.set_text(self.current_item['login']['password'])
          self.textbuffer.set_text(self.current_item['text'])
          self.sidebar_reset_edit()
       self.hide_save()


   # This is used after hitting a cancel button to ensure all entries present
   # on the side_bar are actually present in self.data
   def remove_bad_sidebar_entries(self):
      for i in range(0, len(self.listmodel)):
         try:
            path = Gtk.TreePath(i)
            treeiter = self.listmodel.get_iter(path)
            label_name = self.listmodel.get_value(treeiter, 0)
            label_value = self.listmodel.get_value(treeiter, 1)
            found = False
            for item in self.data['encrypted_item']:
                if str(item['id']) == label_value:
                    found = True
            if found == False:
                self.listmodel.remove(treeiter)
         except Exception:
            pass # index may not be present because we removed it already.


   # Grabs the next available ID, this is used during creation of a new entry
   def get_next_id_number(self):
       id = 0
       for data in self.data['encrypted_item']:
           if int(data['id']) > id:
               id = int(data['id'])
       return(id + 1)

   # Encrypts an incoming string and writes it to the file.
   def encrypt(self, in_content, out_file_name, password, key_length=32):
       in_file = StringIO(in_content)
       out_file = open(out_file_name, 'wb')
       bs = AES.block_size
       salt = Random.new().read(bs - len('Salted__'))
       key, iv = derive_key_and_iv(password, salt, key_length, bs)
       cipher = AES.new(key, AES.MODE_CBC, iv)
       out_file.write('Salted__' + salt)
       finished = False
       while not finished:
           chunk = in_file.read(1024 * bs)
           if len(chunk) == 0 or len(chunk) % bs != 0:
               padding_length = (bs - len(chunk) % bs) or bs
               chunk += padding_length * chr(padding_length)
               finished = True
           out_file.write(cipher.encrypt(chunk))

   # Decrypts a file and returns a string with the contents of the file
   def decrypt(self, file_name, password, key_length=32):
       in_file = open(file_name, 'rb')
       bs = AES.block_size
       salt = in_file.read(bs)[len('Salted__'):]
       key, iv = derive_key_and_iv(password, salt, key_length, bs)
       cipher = AES.new(key, AES.MODE_CBC, iv)
       next_chunk = ''
       results = ''
       finished = False
       while not finished:
           chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
           if len(next_chunk) == 0:
               padding_length = ord(chunk[-1])
               chunk = chunk[:-padding_length]
               finished = True
           results = results + chunk
       return results

   def decrypt_original(self, in_file, out_file, password, key_length=32):
       bs = AES.block_size
       salt = in_file.read(bs)[len('Salted__'):]
       key, iv = derive_key_and_iv(password, salt, key_length, bs)
       cipher = AES.new(key, AES.MODE_CBC, iv)
       next_chunk = ''
       finished = False
       while not finished:
           chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
           if len(next_chunk) == 0:
               padding_length = ord(chunk[-1])
               chunk = chunk[:-padding_length]
               finished = True
           out_file.write(chunk)

   def encrypt_original(self, in_file, out_file, password, key_length=32):
       bs = AES.block_size
       salt = Random.new().read(bs - len('Salted__'))
       key, iv = derive_key_and_iv(password, salt, key_length, bs)
       cipher = AES.new(key, AES.MODE_CBC, iv)
       out_file.write('Salted__' + salt)
       finished = False
       while not finished:
           chunk = in_file.read(1024 * bs)
           if len(chunk) == 0 or len(chunk) % bs != 0:
               padding_length = (bs - len(chunk) % bs) or bs
               chunk += padding_length * chr(padding_length)
               finished = True
           out_file.write(cipher.encrypt(chunk))

   def error(self, message):
      error_dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,Gtk.ButtonsType.CANCEL, "Error")
      error_dialog.format_secondary_text(message)
      error_dialog.run()
      error_dialog.destroy()


def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]


class DialogExample(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "My Dialog", parent, 0,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_default_size(150, 100)
        label = Gtk.Label("This is a dialog to display additional information")
        box = self.get_content_area()
        box.add(label)
        self.show_all()

def password_prompt(parent, message, title=''):
   password_popup = Gtk.MessageDialog(parent,
                                    Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                    Gtk.MessageType.QUESTION,
                                    Gtk.ButtonsType.OK_CANCEL,
                                    message)

   password_popup.set_title(title)
   password_dialog = password_popup.get_content_area()
   password_entry = Gtk.Entry()
   password_entry.set_visibility(False)
   password_entry.set_invisible_char("*")
   password_entry.set_size_request(10,0)
   password_entry.set_activates_default(True)
   password_ok_button = password_popup.get_widget_for_response(response_id=Gtk.ResponseType.OK)
   password_ok_button.set_can_default(True)
   password_ok_button.grab_default()
   password_dialog.pack_end(password_entry, False, False, 0)
   password_popup.show_all()
   response = password_popup.run()
   if (response == Gtk.ResponseType.OK) and (password_entry.get_text() != ''):
      global password
      password = password_entry.get_text().strip()
      password_popup.destroy()
      return
   else:
      quit()


win = MyWindow()
win.connect("delete-event", Gtk.main_quit)
win.startup()
Gtk.main()
