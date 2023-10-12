# Multi monitor Wallpaper Changer for GNOME
Simple script to rotate wallpapers for Multiplt monitors

Currently just grabs wallpaper from NASA POD.

To run make sure you have a NASA API key and then do

```
export NASA_API_KEY=<your api key>
./wallpaper.sh
```

Install in crontab to run at boot or everyday etc.

Eg. this line would change wallpaper every minute.

```
* * * * * export NASA_API_KEY=<my_key>; /home/jon/dev/wallpaper/wallpaper.sh  >> /home/jon/dev/wallpaper/wallpaper.log 2>&1 
```