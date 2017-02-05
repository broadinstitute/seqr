# edit /etc/fstab to auto-mount disk on startup to both /local and /dev/disk/by-id/google-seqr-disk
echo UUID=`sudo blkid -s UUID -o value /dev/disk/by-id/google-seqr-disk` /mnt/disks/google-seqr-disk ext4 discard,defaults,nofail 0 2 | sudo tee -a /etc/fstab
echo '/mnt/disks/google-seqr-disk	/local	none	bind	0	0' | sudo tee -a /etc/fstab
