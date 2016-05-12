cd css/
wget https://fonts.googleapis.com/css?family=Lato:300,400,900 -O lato.css

for i in \
    cdnjs.cloudflare.com/ajax/libs/semantic-ui/2.1.8/semantic.css  \
    cdn.datatables.net/t/dt/dt-1.10.11,r-2.0.2,sc-1.4.1/datatables.min.css \
    cdn.datatables.net/1.10.11/css/dataTables.semanticui.min.css; do 


    wget $i; 
done

cd ../js/

for i in \
    cdnjs.cloudflare.com/ajax/libs/jquery/3.0.0-beta1/jquery.js \
    cdnjs.cloudflare.com/ajax/libs/semantic-ui/2.1.8/semantic.js \
    cdn.datatables.net/t/dt/dt-1.10.11,r-2.0.2,sc-1.4.1/datatables.min.js \
    cdn.datatables.net/1.10.11/js/dataTables.semanticui.min.js; do 
   
    wget $i; 
done;

    
    

