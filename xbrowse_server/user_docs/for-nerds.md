For Nerds: Software and Bioinformatics in xBrowse
================================================

Our main goal with xBrowse if of course to build a useful tool.
When we first decided to build xBrowse, Mark and Dan afforded me much freedom in how to build it.
Along the way, we've also acquired at a secondary goal:
to create a model for how to develop bioinformatics software.
I've tried to apply as many bioinformatics best practices to xBrowse.

### Testing

### Open Source

All of the analysis code in xBrowse is open source, and can be run locally on multiple platforms.

### Version Control

xBrowse uses git for version control.

### Python

### Changing Data

### One Platform for Producers and Consumers

It's always frustrated me that the people who perform bioinformatics - the *producers* -
tend to use fundamentally different systems than *consumers* - the people who review their results.
For example, an analyst may generate a series of statistics on the command line using R,
then export them to excel and email an annotated spreadsheet to her supervisor.

In my opinion, analysis is much more robust if all researchers use the same platform.
In the scenario above, suppose the researcher could send her supervisor a link to the statistics *within R*,
complete with a full command history. This would be more efficient, eliminate a certain class of analysis error,
and provide a more productive interface for researchers with different specialties.

We've tried to follow this philosophy with xBrowse. All of the analyses can be bookmarked and viewed persistently;
there is no need to leave the platform. Analyses are also fully traceable -
if you share a link with a collaborator, she can view the full analysis without explanation.

### Scriptable

### Separation of Methods and Implementation

