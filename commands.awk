/CommandHandler\(/ {
	printf 
		substr($2,1, length($2)-2)
		" - ";
	for (i=4; i<=NF; i++) 
		printf $i (i<NF ? OFS : ORS)
}
