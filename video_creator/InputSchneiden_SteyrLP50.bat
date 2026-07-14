echo schuss bei 2.6 sekunden
eche 
ffmpeg -ss 00:00:00.00 -t 00:00:01.30 -i A_high_quality_cinematic_vide.mp4 -filter_complex "[0:v]split=2[v1][v2];[v2]reverse[v2_rev];[v1][v2_rev]concat=n=2:v=1:a=0[v]" -map "[v]" -c:v libx264 -crf 18 B.mp4
pause
ffmpeg -ss 00:00:00.01 -i A_high_quality_cinematic_vide.mp4 -vframes 1 standbild_SteyrLP50.png
pause