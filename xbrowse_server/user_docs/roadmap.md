Roadmap
=== 

### Background

Development of xBrowse began in April 2012, as an internal web application at ATGU. 
The original goal was simply to provide a web interface for our clinical and molecular biology collaborators
to browse the variants in a VCF file. 

As we acquired more users and received more feature requests, 
we realized that xBrowse would have to become more robust and feature complete. 
We also realized that it didn't make sense to develop xBrowse in a vacuum at ATGU -
that we could only justify the investment if xBrowse were to become more widely used. 

### Vision

As I write this in October 2013, our long term (6-8 month) vision for xBrowse is to develop a robust open source platform 
that can serve a range of uses in rare disease genomics, at a variety of institutions. This involves a few things: 

- **Community**: An important part of this vision is fostering a community - both researchers and developers - to 
help guide the development of xBrowse. 

- **Continuous Feature Development**: Many research software programs reach a single release and then development stops, as authors move on to other projects. (Cynical readers could perhaps suggest a connection to the publication of a paper.) 
We have a different goal with xBrowse; we anticipate many exciting developments in Mendelian disease genomics in the coming years, 
and we want to integrate these ideas in xBrowse as they are discovered. 

### Beta Version

At this time, xBrowse is still under active development and should be considered "Beta" software. 
As we work toward a first public release, we host an instance of xBrowse at ATGU, available at atgu.mgh.harvard.edu/xbrowse. 

If you want to be a Beta user of xBrowse, contact Brett at [bthomas@broadinstitute.org](mailto://bthomas@broadinstitute.org). 
I will show you how to upload a VCF file to our FTP setver and begin experiementing with xBrowse. 

### Tiered Release

We mention *open source* throughout these documentation - we are firmly committed to keeping xBrowse free and open source. 
However, open sourcing xBrowse poses a unique set of challenges, since it is a public web application with highly sensitive data. 

So, during this interim period, we are experimenting with a tiered release. 
We are happy to send the code to any friendly coders that want to review the code and install a local version of xBrowse. 
I will caution that this is a nontrivial exercise, and we can't affort to get too distracted supporting external installations, 
but we would greatly appreciate anybody that has the time to take this on. 

Also note that we have split the xBrowse code base into two repositories. 
The analysis library is public at github.com/brettpthomas/xbrowse, though it isn't self-sufficient yet.