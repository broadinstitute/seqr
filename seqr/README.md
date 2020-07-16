- [ ] All unit test are passing and coverage has not substantively dropped
- [ ] No new dependency vulnerabilities have been introduced
- [ ] Static assets have been built and committed if needed
- [ ] If any python requirements are updated, they are noted and here and will be updated before deploying: 
- [ ] Any database migrations are noted here, and will be run before deploying: 
- [ ] Any new endpoints are explicitly tested to ensure they are only accessible to correctly permissioned users
- [ ] No secrets have been committed
- [ ] Infrastructure changes:
  - [ ] No changes to the required seqr infrastructure are included in this change 
  
  OR 
  
  - [ ] Changes to seqr's infrastructure are already been deployed to a new docker image, and these changes will be released via that image 
  - [ ] All these changes have been tested before release on the docker image
  - [ ] All these changes have bee vetted for potential vulnerabilities