#!/usr/bin/python
#
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

load_file = 'encrypted_file.txt'
password = "password"

class MyWindow(Gtk.Window):
   def __init__(self):
      Gtk.Window.__init__(self, title="Encrypted Notebook")
      self.grid = Gtk.Grid()
      # Load in data:
      self.load_data_from_file(load_file)
      self.create_password_area()
      self.create_side_bar()
      self.create_notes_area()
      self.create_save_cancel()
      self.create_right_click_menu()
      self.add(self.grid)

      # Used for the clipboard:
      self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
      self.clipboard_mouse = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)

      # Initial variables set
      self.current_item = None
      self.sidebar_current_selection = 0
      self.sidebar_locked = False


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
       self.password_area.add(username_label)
       self.password_area.attach_next_to(self.username_text, username_label, Gtk.PositionType.RIGHT, 1, 1)
       self.password_area.attach_next_to(password_label, username_label, Gtk.PositionType.BOTTOM, 1, 1)
       self.password_area.attach_next_to(self.password_text, password_label, Gtk.PositionType.RIGHT, 1, 1)
       self.password_area.attach_next_to(show_password, self.password_text, Gtk.PositionType.RIGHT, 1, 1)
       self.grid.attach(self.password_area, 1, 0, 1, 1)

   def edit_changed(self, widget):
       if self.needs_saving() == True:
           self.show_save()
           self.sidebar_locked = True
           print("contents changed")
       else:
           self.hide_save()
           self.sidebar_locked = False
           print("contents are good now")


   def show_save(self):
       self.save_cancel_area.show()
       print("gott save")

   def hide_save(self):
       self.save_cancel_area.hide()
       print("gotta hide")

   def create_side_bar(self):
       self.listmodel = Gtk.ListStore(str, str)
       self.listmodel.append(["Add New Entry", "Add New Entry"])
       for entry in self.data['encrypted_item']:
           print("Got one:")
           print(entry['name'])
           self.listmodel.append([entry['name'], str(entry['id'])])
       self.side_bar_box = Gtk.TreeView.new_with_model(self.listmodel)
       renderer = Gtk.CellRendererText()
       renderer.set_property("editable", True)
       renderer.connect("edited", self.side_bar_edited)
       column = Gtk.TreeViewColumn("Title", renderer, text=0)
       column.set_sort_column_id(0)
       self.side_bar_box.append_column(column)
       yeah = self.side_bar_box.get_selection()
       yeah.set_select_function(self.bah, None)
       self.row_activation_id = self.side_bar_box.connect("row-activated", self.side_bar_button_clicked)
       self.side_bar_box.connect("button_release_event", self.side_bar_button_right_clicked)
       self.side_bar_box.set_activate_on_single_click(True)
       self.grid.attach(self.side_bar_box, 0, 0, 1,2)

   def create_right_click_menu(self):
      self.right_click_menu = Gtk.Menu()
      add_password = Gtk.MenuItem("Add Password")
      add_password.connect("button_release_event", self.add_password)
      self.right_click_menu.append(add_password)
      self.right_click_menu.show_all()

   def add_password(self, widget, yeah):
      self.password_area.show()
      print("add password")

   def side_bar_button_right_clicked(self, value1, value2):
       if value2.button == 3:
          print(self.sidebar_current_selection)
          if self.sidebar_current_selection != None:
             self.sidebar_select_number(self.sidebar_current_selection)
             tree_sel = self.side_bar_box.get_selection()
             (name, stuff) = tree_sel.get_selected()
             print(str(name))
             self.right_click_menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())
             print(name.get_value(stuff, 0))
          print("Right clicked")
          return False


   def side_bar_button_clicked(self, value1, value2, value3):
       self.textview.set_editable(True)
       if self.needs_saving() == True:
           self.sidebar_locked = True
       if self.sidebar_locked == True:
          print("skipping")
       else:
          self.side_bar_box.handler_unblock(self.row_activation_id)
          path = Gtk.TreePath(value2)
          treeiter = self.listmodel.get_iter(path)
          label_name = self.listmodel.get_value(treeiter, 0)
          label_value = self.listmodel.get_value(treeiter, 1)
          print(label_name)
          print(label_value)
          if label_value == "Add New Entry":
              print("You clicked new entry")
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


   def bah(self, value1, value2, value3, value4, value5):
      if self.sidebar_locked == True:
          #yeah = self.side_bar_box.get_selection()
          #yeah.set_select_function(self.bah2, None)
          #self.side_bar_box.handler_unblock(self.row_activation_id)
          print('bah_false')
          return False
      else:
         print('bah_true')
         return True


   def sidebar_select_number(self, number):
       print("selecting item in sidebar : %s" %(number))
       path = Gtk.TreePath(number)
       select = self.side_bar_box.get_selection()
       select.select_path(path)

   def sidebar_reset_edit(self):
       if self.sidebar_reset_name != None:
           path = Gtk.TreePath(self.sidebar_current_selection)
           treeiter = self.listmodel.get_iter(path)
           self.listmodel.set_value(treeiter, 0, self.sidebar_reset_name)
           self.current_item['name'] = self.sidebar_reset_name
           self.sidebar_reset_name = None
           #label_value = self.listmodel.get_value(treeiter, 1)

   def create_notes_area(self):
       self.scrolledwindow = Gtk.ScrolledWindow()
       self.scrolledwindow.set_hexpand(True)
       self.scrolledwindow.set_vexpand(True)
       self.grid.attach(self.scrolledwindow, 1, 1, 1, 1)
       self.textview = Gtk.TextView()
       self.textbuffer = self.textview.get_buffer()
       self.textbuffer.connect("changed", self.edit_changed)
       self.scrolledwindow.add(self.textview)
       self.textview.set_editable(False)

   def copy_password(self, thing):
       self.clipboard.set_text(self.password_text.get_text(), -1)
       self.clipboard_mouse.set_text(self.password_text.get_text(), -1)
       print("Copied!")
   
   # This will display/unhide the text in the password field.
   def show_password(self, button):
        value = button.get_active()
        self.password_text.set_visibility(value)


   def populate_fields(self):
       if self.current_item == None or self.current_item == "Adding New Entry":
          self.username_text.set_text('')
          self.password_text.set_text('')
          self.textbuffer.set_text('')
       else:
          self.username_text.set_text(self.current_item['login']['username'])
          self.password_text.set_text(self.current_item['login']['password'])
          self.textbuffer.set_text(self.current_item['text'])
       if self.username_text.get_text() == '' and self.password_text.get_text() == '':
          self.password_area.hide()
       else:
          self.password_area.show()

   def load_data_from_file(self, file_name):
       if not os.path.isfile(file_name):
          content = open('encrypted_file_example.txt')
          self.encrypt(content.read(), file_name, password)
          #with open('encrypted_file_example.txt', 'rb') as in_file, open(file_name, 'wb') as out_file:
          #  self.encrypt(in_file, out_file, password)
       encrypted_file = self.decrypt(file_name, password)
       #encrypted_file = open(file_name)
       #self.data = json.load(encrypted_file)
       #self.data = json.load(StringIO(encrypted_file))
       self.data = yaml.safe_load(StringIO(encrypted_file))
       print(str(self.data))
       print(self.data['note_version'])

   def side_bar_edited(self, widget, path, text):
      self.listmodel[path][0] = text
      self.sidebar_reset_name = self.current_item['name']
      self.current_item['name'] = text
      self.sidebar_locked = True
      self.show_save()
      print("Edited!")


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
       elif self.current_item == "Adding New Entry":
           print("Adding new entry always needs to be saved")
           return True
       else:
          if self.current_item['login']['username'] != self.username_text.get_text():
             return True
          if self.current_item['login']['password'] != self.password_text.get_text():
             return True
          print(str(self.textbuffer.get_bounds()))
          if self.current_item['text'] != self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False):
             return True
       return False



   def save_button_clicked(self, widget):
       self.sidebar_locked = False
       self.sidebar_reset_name = None
       if self.current_item == "Adding New Entry":
           print("Trying to save a new entry...")
           if self.sidebar_current_selection != None:
              new_item = {}
              path = Gtk.TreePath(self.sidebar_current_selection)
              treeiter = self.listmodel.get_iter(path)
              label_name = self.listmodel.get_value(treeiter, 0)
              new_item['name'] = label_name
              new_item['id'] = self.get_next_id_number()
              new_item['text'] = self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False)
              new_item['login'] = {}
              new_item['login']['username'] = self.username_text.get_text()
              new_item['login']['password'] = self.password_text.get_text()
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
              print("Saved new item")
              self.remove_bad_sidebar_entries()
       if not self.current_item == None:
          self.current_item['login']['username'] = self.username_text.get_text()
          self.current_item['login']['password'] = self.password_text.get_text()
          self.current_item['text'] = self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), False)
          print("Saved existing item")
          print(str(self.current_item))
       print("Save clicked")
       yeah = open("out_file.txt", 'w')
       yeah.write(str(self.data))
       yeah.close()
       self.encrypt(str(self.data), load_file, password)

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
       print(str(json.dumps(self.data)))
       print("Cancel clicked")


   def remove_bad_sidebar_entries(self):
      for i in range(1, len(self.listmodel)):
         try:
            path = Gtk.TreePath(i)
            treeiter = self.listmodel.get_iter(path)
            label_name = self.listmodel.get_value(treeiter, 0)
            label_value = self.listmodel.get_value(treeiter, 1)
            found = False
            for item in self.data['encrypted_item']:
                if str(item['id']) == label_value:
                    print("Found %s" %(label_value))
                    found = True
            if found == False:
                print("values didn't match: %s " %(label_value) )
                self.listmodel.remove(treeiter)
         except Exception:
            pass # index may not be present because we removed it already.

   def get_next_id_number(self):
       id = 0
       for data in self.data['encrypted_item']:
           if int(data['id']) > id:
               id = int(data['id'])
       return(id + 1)




   def encrypt(self, in_content, out_file_name, password, key_length=32):
       print "I got this as content:"
       print in_content
       in_file = StringIO(in_content)
       out_file = open(out_file_name, 'wb')
       print("Encrypting...")
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


   def decrypt(self, file_name, password, key_length=32):
       print("Decrypting...")
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
       print("returning this:")
       print(str(results))
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

win = MyWindow()
win.connect("delete-event", Gtk.main_quit)
win.startup()
Gtk.main()
