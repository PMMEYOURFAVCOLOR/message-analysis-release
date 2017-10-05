#!/bin/bash

# Requirements: Python 3.6 (or later) with matplotlib, praw, and pyperclip
#
# The simplest setup method is to install Anaconda, a Python data science
# platform (which includes matplotlib by default), from
# https://www.anaconda.com/download/
# You will still have to manually install praw to run messagearchive.py,
# and pyperclip to run hash-name-with-salt.py,
# but dbazr.py works with a fresh Anaconda Python environment.
# To install those modules, run
# /path/to/anaconda/Scripts/pip.exe install praw pyperclip
#
# An alternative setup method is through Cygwin, a Linux style shell for
# Windows.  Download it from
# https://cygwin.com/install.html
#
# After installing the minimal base packages, re-run the installer and
# install the package lynx (a command line web browser).
# With lynx installed, drop this file (setup.sh) into your Cygwin
# environment's home directory, /path/to/cygwin/home/yourname/
#
# Start the Cygwin terminal either through the shorcut the installer made,
# using a windows shell by running /path/to/cygwin/Cygwin.bat,
# or by running Mintty directly from /path/to/cygwin/bin/mintty.exe
# Finally, make the script executable and run it by typing
# chmod 777 ~/setup.sh && ~/setup.sh
#
# NOTE: The copy to clipboard feature in hash-name-with-salt.py does not work
# with Cygwin.  While the script will still return a hash, a non-cygwin version
# of Python (like Anaconda) must be used to access the clipboard.

lynx -source rawgit.com/transcode-open/apt-cyg/master/apt-cyg > ~/apt-cyg
install ~/apt-cyg /bin
rm -f ~/apt-cyg

apt-cyg install nano pkg-config ghostscript libfreetype-devel libpng-devel \
    libgtk2.0-devel gcc-g++ git openbox python3 python3-numpy python3-pyqt5 \
    python3-devel libX11-devel
easy_install-3.6 pip
pip install --upgrade six


# This section can potentially make your .bashrc messy if setup is run
# multiple times.  To avoid that, delete every line below this comment.
# When the script finishes, restart cygwin.
# After restarting cygwin, run 'pip install matplotlib praw'.
epochTime=`date +%s`
echo "The existence of this file triggers an if-then statement in"\
 > ~/.$epochTime.python.trigger
echo "~/.bashrc  to install matplotlib and praw for python."\
 >> ~/.$epochTime.python.trigger
echo "if [ -f ~/.$epochTime.python.trigger ]; then"\
 >> ~/.bashrc
echo "    pip install matplotlib praw pyperclip"\
 >> ~/.bashrc
echo "    echo 'Install complete.'"\
 >> ~/.bashrc
echo "    echo 'Remember to use package python3, not python.'"\
 >> ~/.bashrc
echo "    rm -f ~/.$epochTime.python.trigger"\
 >> ~/.bashrc
echo "fi"\
 >> ~/.bashrc
echo 'Please restart cygwin to complete installation.'