echo schuss bei 2.6 sekunden
eche 
ffmpeg -ss 00:00:02.15 -i Precision_Air_Pistol_Shot_Simulation.mp4 -t 00:00:04.75 -c:v libx264 -crf 18 schuss.mp4
pause
ffmpeg -ss 00:00:02.15 -i Precision_Air_Pistol_Shot_Simulation.mp4 -vframes 1 standbild.png
pause