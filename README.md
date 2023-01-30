# CT5_Dropbox_Backup

Backup dropbox files onto partitions with unsupported file systems, such as exFAT.

This script never changes files on the cloud server.

**Note that this script will remove any local file under the specified backup folder. So make sure you select an empty local folder as your local backup folder.**

## Before running the script

You should register for an app in your Dropbox account by going to [https://www.dropbox.com/developers/apps?_tk=pilot_lp&_ad=topbar4&_camp=myapps](https://www.dropbox.com/developers/apps?_tk=pilot_lp&_ad=topbar4&_camp=myapps).

Click `Create App` and follow the online prompt.

Once finished, go to your app:
- In the `Permissions` tab, tick `account_info.read`, `files.metadata.read`, and `files.content.read` and then click `submit` at the bottom of the page.
- In the `Settings` tab, go to section `OAuth 2` and click **`Generate`** button under `Generated access token`. 
  - Keep this safe for copy and paste onto the terminal when you run this script.
  - **Never ever reveal this to anyone else or post this onto public channels.**

## Package dependencies

This script uses the native Dropbox Python API along with some other common Python packages. This scripted was tested in Python 3.9 interpreter, but should work well using other Python 3 interpreters.

To ensure you have every package installed, try running the following command in terminal:
```
pip install pickle, tkinter, dropbox
```

## Using the script

Pull down both python script files and run the "dropbox_backup_v3.py" script.

Follow the prompt on commandline and onscreen dialogs and you should be fine.
