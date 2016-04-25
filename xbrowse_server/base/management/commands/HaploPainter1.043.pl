#!/usr/bin/perl

###########################################################################
#                                                                         #
#                         H A P L O P A I N T E R                         #
#                                                                         #
#      +==========================================================+       #
#      |                                                          |       #
#      |         Copyright (c) 2004-2008 Holger Thiele            |       #
#                        All rights reserved.                     |       #
#      |              This program is free software.              |       #
#      |         You can redistribute it and/or modify it         |       #
#      |       under the terms of GNU General Public License      |       #
#      |        as published by the Free Software Foundation.     |       #
#      |                                                          |       #
#      +==========================================================+       #
#                                                                         #
#                                                                         #
###########################################################################

use Cairo;
use Data::Dumper;
use DBI;
use File::Basename;
use File::Spec::Functions;
use Gtk2;
use Math::Trig; 
use Sort::Naturally;
use Storable qw /freeze thaw retrieve store /;
use strict;
use subs qw / _MainMenu _ContextMenu /;
use Tk;
use Tk::BrowseEntry;
use Tk::DialogBox;
use Tk::LabFrame;
use Tk::NoteBook;
use Tk ':variables';
use vars qw / $mw $canvas $menubar $self $batch/ ;
use warnings;

$Data::Dumper::Sortkeys =1;

###########################################################################

### global variables not for export
my $param = {	
	ENCODING => 'utf8',
	EXPORT_FORMATS => { PS => 1, PDF => 1, SVG => 1, PNG => 1 },
	GLOBAL_MAP_IMPORT => 0,
	HAPLOTYPE_FORMATS => { allegro => 1, genehunter => 1, merlin => 1, simwalk => 1 },
	LAST_CHANGE		=> '15.10.08',
	MAP_FORMATS => { 1 => 1, 2 => 1 },
	MAX_COUNT => 120,
	PAPER_SIZE		=> {
			A0 	=> { X => 840, Y => 1189 },
			A1 	=> { X => 594, Y => 840  },
			A2 	=> { X => 420, Y => 594  },
			A3 	=> { X => 297, Y => 420  },
			A4 	=> { X => 210, Y => 297  },
			A5 	=> { X => 148, Y => 210  },
			B4 	=> { X => 257, Y => 364  },
			B5 	=> { X => 182, Y => 257  },
			Ledger 	=> { X => 432, Y => 279  },
			Letter 	=> { X => 216, Y => 279  },
			Legal 	=> { X => 216, Y => 356  },
			'11x17' => { X => 279, Y => 432  }
	},
	PEDEGREE_FORMATS => { linkage => 1, csv => 1 },
	SHOW_GRID => 1,
	SORT_BY_PEDID => 0,
	SORT_COUPLE_BY_GENDER => 0,
	WRITE_BOM => 1
};

### default values global and famliy specific
my $def = {
	GLOB => {
		BACKGROUND => '#ffffff', 
		BORDER => 20,
		CURSOR => 'left_ptr',
		DB_TYPE => '',
		DB_PORT => '',
		DB_SID => '',
		DB_HOST => '',
		DB_UNAME => '',
		DB_PASSWD => '',
		DB_RELATION => '',
		ORIENTATION 	=> 'Landscape',
		PAPER	=> 'A4',						
		RESOLUTION_DPI  => 96,
		STATUS => 0,
		STRUK_MODE => 0,
		VERSION	=> '1.043'
	},
	FAM => {
		ADOPTED_SPACE1 => 5,
		ADOPTED_SPACE2 => 3,
		AFF_COLOR => {
			0 => '#c0c0c0',
			1 => '#ffffff',
			2 => '#000000',
			3 => '#ff7f50',
			4 => '#ffd700',
			5 => '#6b8e23',
			6 => '#1e90ff',
			7 => '#ba55d3',
			8 => '#adff2f',
			9 => '#ffffff',  # dummy sample
		},
		ALIGN_LEGEND => 1,
		ALIVE_SPACE => 5,
		ALLELES_SHIFT => 15,
		ARROW_COLOR => '#000000',
		ARROW_DIST1 => 7,
		ARROW_DIST2 => 9,
		ARROW_DIST3 => 4,
		ARROW_LENGTH => 13,
		ARROW_LINE_WIDTH => 1.5,		
		ARROW_SYM_DIST => 5,		
		BBOX_WIDTH => 35,
		BREAK_LOOP_OK => {},
		CASE_INFO_SHOW => { 1 => 1, 2 => 0, 3 => 0, 4 => 0, 5 => 0 },
		CONSANG_DIST => 4,
		COUPLE_REL_DIST => 0.25,   # space between symbols in couple
		CROSS_FAKTOR1 => 1,
		EXPORT_BACKGROUND => 0,
		FILL_HAPLO => 1,
		FONT1 => {
			COLOR => '#000000',
			FAMILY => 'Arial',
			SIZE => 16,
			SLANT => 'roman',
			WEIGHT => 'bold'
		},
		FONT_HAPLO => {
			COLOR => '#000000',
			FAMILY => 'Arial',
			SIZE => 14,
			SLANT => 'roman',
			WEIGHT => 'bold'
		},
		FONT_HEAD => {
			COLOR => '#000000',
			FAMILY => 'Arial',      
			SIZE => 30,
			SLANT => 'roman',
			WEIGHT => 'bold'
		},
		FONT_INNER_SYMBOL => {
			COLOR => '#000000',
			FAMILY => 'Arial',
			SIZE => 16,
			SLANT => 'roman',
			WEIGHT => 'bold'
		},
		FONT_PROBAND => {
			COLOR => '#000000',
			FAMILY => 'Arial',
			SIZE => 12,
			SLANT => 'roman',
			WEIGHT => 'bold'
		},
		FONT_MARK => {
			COLOR => '#000000',
			FAMILY => 'Arial',
			SIZE => 12,
			SLANT => 'roman',
			WEIGHT => 'bold'
		},
		GITTER_X => 25,
		GITTER_Y => 25,
		HAPLO => {},
		HAPLO_LW => 1,
		HAPLO_SEP_BL => 0,
		HAPLO_SPACE => 9,
		HAPLO_TEXT_LW => 0,
		HAPLO_UNKNOWN => 0,
		HAPLO_UNKNOWN_COLOR => '#000000',
		HAPLO_WIDTH => 12,
		HAPLO_WIDTH_NI => 4,
		LEGEND_SHIFT_LEFT => 200,
		LEGEND_SHIFT_RIGHT => 50,
		LINE_COLOR => '#000000',
		LINE_WIDTH => 3,          # width of line that connects symbols (was 1)
		LINE_SIBS_Y => 40,
		LINE_CROSS_Y => 15,
		LINE_TWINS_Y => 35,
		LOOP_BREAK_STATUS => 0,
		MARKER_POS_SHIFT => 155,
		PED_ORG => {},
		PROBAND_SIGN => 'P',
		SHOW_COLORED_TEXT => 0,
		SHOW_GENDER_SAB => 1,
		SHOW_HAPLO_BAR => 1,
		SHOW_HAPLO_BBOX => 1,
		SHOW_HAPLO_NI_0 => 1,
		SHOW_HAPLO_NI_1 => 1,
		SHOW_HAPLO_NI_2 => 1,
		SHOW_HAPLO_NI_3 => 0,
		SHOW_HAPLO_TEXT => 1,
		SHOW_HEAD => 0,             # Adds title to image (eg. 'Family A') (was 1)
		SHOW_LEGEND_LEFT => 0,
		SHOW_LEGEND_RIGHT => 0,
		SHOW_MARKER => 1,
		SHOW_POSITION => 1,
		SHOW_INNER_SYBOL_TEXT => 1,
		SYMBOL_LINE_COLOR => '#000000',      # line color was blue (0000ff)
		SYMBOL_LINE_WIDTH => 3,              # symbol outline (was 2)
		SYMBOL_SIZE => 40,                   # symbol size (was 25)
		SYMBOL_LINE_COLOR_SET => 0,
		X_SPACE => 7,             # horizontal space between symbols (was 3)
		Y_SPACE => 4,             # vertical separation between generations (was 6)
		Y_SPACE_DEFAULT => 4,     # vertical separation between generations (was 6)
		Y_SPACE_EXTRA => 15,
		ZOOM => 1
	}
};


Main();


# Main Tk Window with Canvas and bindings
#=========
sub Main {
#=========
	
	MakeSelfGlobal();	
	ExecuteBatchMode();
	exit if $batch;
		
	$mw = MainWindow->new(-title => "HaploPainter V.$self->{GLOB}{VERSION}");
	$mw->withdraw;
	my $scr_x  = $mw->screenwidth;
	my $scr_y  = $mw->screenheight;
	my $mw_szx = 0.75;
	my $mw_szy = 0.65;

	$mw->geometry (
		int($scr_x*$mw_szx) . 'x' . int($scr_y * $mw_szy) .  '+' .
		int($scr_x*(1-$mw_szx)/2) . '+' . int($scr_y * (1-$mw_szy)/3)
	);
		
	### Attaching the menu from Main Window
	$mw->configure(-menu => $menubar = $mw->Menu(-menuitems => _MainMenu));

	### proper view of font size
	$mw->scaling(1);
	
	my $f1 = $mw->Frame(-relief => 'groove', -borderwidth => 2)->pack(qw/-fill x/);
	my $f2 = $mw->Frame(-relief => 'groove', -borderwidth => 2)->pack(qw/-fill x/);
	my ($b1,$b2,$b3,$b4,$b5,$b6);
	
	### navigation menue buttons (ugly cursor shapes due to Tk)
	$b1=$f1->Button(-image => $mw->Photo(-format => 'gif', -data => &GetArrow), -relief => 'sunken', -command => sub {
		$b1->configure(-relief => 'sunken');
		foreach ($b2,$b3,$b4) { $_->configure(-relief => 'flat') }
		$self->{GLOB}{CURSOR} = 'left_ptr';
		$self->{GLOB}{STATUS} = 0
	})->pack(qw/-side left/);
	$b2=$f1->Button(-image => $mw->Photo(-format => 'gif', -data => &GetPlus), -relief => 'flat', -command => sub {
		$b2->configure(-relief => 'sunken');
		foreach ($b1,$b3,$b4) { $_->configure(-relief => 'flat') }
		$self->{GLOB}{CURSOR} = 'plus';
		$self->{GLOB}{STATUS} = 1
	})->pack(qw/-side left/);
	$b3=$f1->Button(-image => $mw->Photo(-format => 'gif', -data => &GetMinus), -relief => 'flat', -command => sub {
		$b3->configure(-relief => 'sunken');
		foreach ($b1,$b2,$b4) { $_->configure(-relief => 'flat') }
		$self->{GLOB}{CURSOR} = 'circle';
		$self->{GLOB}{STATUS} = 2
	})->pack(qw/-side left/);
	$b4=$f1->Button(-image => $mw->Photo(-format => 'gif', -data => &GetHand), -relief => 'flat', -command => sub {
		$b4->configure(-relief => 'sunken');
		foreach ($b1,$b2,$b3) { $_->configure(-relief => 'flat') };
		$self->{GLOB}{CURSOR} = 'fleur';
		$self->{GLOB}{STATUS} = 3
	})->pack(qw/-side left/);	
	$b5=$f1->Button(-image => $mw->Photo(-format => 'gif', -data => &GetNextLeft), -relief => 'flat', -command => sub {		
		DrawNextFamily(1);
	})->pack(qw/-side left/);
	$b6=$f1->Button(-image => $mw->Photo(-format => 'gif', -data => &GetNextRight), -relief => 'flat', -command => sub {		
		DrawNextFamily(0);
	})->pack(qw/-side left/);
	
	### Info Label for showing Information during pedigree construction and counting of line crosses
	$param->{INFO_LABEL} = $f1->Label()->pack(qw/-side right/);
	
	### Central Canvas Window
	$canvas = $f2->Scrolled(
		'Canvas',-width => 10000, -height => 10000, -bg => $self->{GLOB}{BACKGROUND},
		-scrollbars => 'osoe', -scrollregion => [ 0,0,2000,2000],-cursor => 'left_ptr',
	)->pack(-expand => 1, -fill => 'both');
		
	my $menu = $canvas->Menu(-tearoff => 0, -menuitems => _ContextMenu);
	
	### Bindigs for all user interaction remaining the main window and canvas drawing elements
	$canvas->CanvasBind('<1>' => [ \&MouseB1Klick, Ev('x'), Ev('y') ]);
	$canvas->CanvasBind('<3>' => [ \&ShowContextMenue, $menu, Ev('x'), Ev('y') ]); 
	$canvas->CanvasBind('<Control-1>' => [ \&MouseB1ControlKlick, Ev('x'), Ev('y') ]);
	$canvas->CanvasBind('<Shift-1>' => [ \&MouseB1ControlKlick, Ev('x'), Ev('y') ]);	
	$canvas->CanvasBind('<ButtonRelease-1>' => [ \&ButtonRelease ]); 	
	$canvas->CanvasBind('<Enter>' => sub { $canvas->configure(-cursor => $self->{GLOB}{CURSOR}) });	
	$canvas->CanvasBind('<Configure>' => \&AdjustView);
	$canvas->CanvasBind('<MouseWheel>' =>[ sub { $_[0]->yview('scroll',-($_[1]/120),'units') }, Tk::Ev('D') ]);			
	$canvas->CanvasBind('<B1-Motion>' => [ \&MouseB1Move, Ev('x'), Ev('y') ]);
	
	$canvas->bind('SYMBOL','<ButtonRelease-1>', [ \&MouseB1Release, Ev('x'),Ev('y') ] );
	$canvas->bind('HEAD', '<ButtonRelease-1>', [ \&HeadB1Release, Ev('x'),Ev('y') ] );
	$canvas->bind('HEAD', '<B1-Motion>' => [ \&MoveHead, Ev('x'), Ev('y') ] );	
	$canvas->bind('ALLEL', '<Leave>', sub {
		$canvas->itemconfigure($self->{GLOB}{ACTIVE_ITEM}, -fill => $self->{GLOB}{ACTIVE_COLOUR});
		delete $self->{GLOB}{ACTIVE_ITEM}
	});
	$canvas->bind('ALLEL', '<Double-1>', \&KlickAllel  );
	$canvas->bind('SYMBOL','<Double-1>', \&KlickSymbol );
	$canvas->bind('HEAD','<Double-1>', \&KlickHead );
	$canvas->bind('ALLEL', '<Enter>', \&EnterAllel );

	$mw->bind('<Control-Key-1>' => sub { ImportMapfile(1) } );
	$mw->bind('<Control-Key-2>' => sub { ImportMapfile(2) } );	
	$mw->bind('<Control-Key-o>' => \&RestoreSelfGUI );	
	$mw->bind('<Control-Key-s>' => sub { SaveSelf(0) } );	
	$mw->bind('<Control-Key-d>' => \&DeleteSID );	
	$mw->bind('<Control-Key-i>' => \&AddSiblings );	
	$mw->bind('<Control-Key-f>' => \&Configuration );	
	$mw->bind('<Control-Key-n>' => \&NewPedigree );		
	$mw->bind('<Key-F1>' => sub { ImportPedfile('LINKAGE') });
	$mw->bind('<Key-F2>' => sub { ImportPedfile('CSV') });
	$mw->bind('<Key-F4>' => \&ImportPedegreeDBI );		
	$mw->bind('<Key-F5>' => \&RedrawPedForce ); 
	$mw->bind('<Key-F6>' => \&ReSetHaploShuffle );
	$mw->bind('<Key-F7>' => \&AdjustView );
	$mw->bind('<Key-F8>' => sub { AdjustView(-fit => 'center') });	
	$mw->bind('<Key-F9>'  => sub { ImportHaplofile('SIMWALK')	 });
	$mw->bind('<Key-F10>' => sub { ImportHaplofile('GENEHUNTER')	 });
	$mw->bind('<Key-F11>' => sub { ImportHaplofile('MERLIN')	 });
	$mw->bind('<Key-F12>' => sub { ImportHaplofile('ALLEGRO')	 });
	$mw->bind('<Key-plus>' => sub { Zoom(1) });
	$mw->bind('<Key-minus>' => sub { Zoom(-1) });	
	$mw->bind('<Key-Delete>' => \&DeleteSID);	
	
	# MainWindow icon
	$mw->idletasks; 
	$mw->iconimage($mw->Photo(-format => 'gif', -data => GetIconData()));
	$mw->deiconify;
	$mw->raise;
	$canvas->Subwidget("canvas")->Tk::focus;

	### assuming the argument is a pedfile to open and draw
	if ($ARGV[0] && scalar @ARGV == 1 && -f $ARGV[0]) { 
		$mw->afterIdle(\&EvalOpenFile, $ARGV[0])
	}	
	
	MainLoop;	
}



# building the whole menu staff at once
#==============
sub _MainMenu {
#==============
	[
		map ['cascade', $_->[0], -menuitems => $_->[1], -tearoff => 0 ],
		[ '~File',
			[	
				[ 'command', 'Open ...',	-command => \&RestoreSelfGUI , -accelerator => 'Contr+O' ],
				[ 'command', 'Open Default ...',	-command => \&OpenDefaults  ],
				[ 'command', 'Save', 		-command => [\&SaveSelf, 0] , -accelerator => 'Contr+S' ],
				[ 'command', 'Save as ..',	-command => [\&SaveSelf, 1] ],				
				,'-',
				[ 'cascade', 'Import Pedigrees ...', -tearoff => 0,	-menuitems =>
					[
						['command', 'Linkage',			-command => [ \&ImportPedfile, 'LINKAGE' ], -accelerator => 'F1' ],
						['command', 'CSV',	-command => [ \&ImportPedfile, 'CSV' ], -accelerator => 'F2' ],
						['command', 'Database',			-command => \&ImportPedegreeDBI, -accelerator => 'F4' ],
					]
				],
				[ 'cascade', 'Import Haplotypes ...', -tearoff => 0,	-menuitems =>
					[
						['command', 'Simwalk',		-command => [ \&ImportHaplofile, 'SIMWALK'		], -accelerator => 'F9' ],
						['command', 'GeneHunter',	-command => [ \&ImportHaplofile, 'GENEHUNTER'	], -accelerator => 'F10' ],
						['command', 'Merlin',		-command => [ \&ImportHaplofile, 'MERLIN' 		], -accelerator => 'F11' ],
						['command', 'Allegro',		-command => [ \&ImportHaplofile, 'ALLEGRO' 		], -accelerator => 'F12' ],
					]
				],
				[ 'cascade', 'Import Map File ...', -tearoff => 0,	-menuitems =>
					[
						['command', 'CHR-POS-MARKER',	-command => [ \&ImportMapfile, 1	], -accelerator => 'Contr+1'  ],
						['command', 'CHR-MARKER-POS',	-command => [ \&ImportMapfile, 2	], -accelerator => 'Contr+2'  ],
					]
				],
				'-',
				[ 'checkbutton', 'Global map import' , -variable => \$param->{GLOBAL_MAP_IMPORT} ],				
				'-',				
				[ 'cascade', 'Export ...', -tearoff => 0, -menuitems =>															
					[
						[ 'command', 'PDF', -command => [ \&ExportSaveDialog,  'PDF' ]  ],
						[ 'command', 'SVG', -command => [ \&ExportSaveDialog,  'SVG' ]  ],								
						[ 'command', 'PNG', -command => [ \&ExportSaveDialog,  'PNG' ]  ],
						[ 'command', 'POSTSCRIPT', -command => [ \&ExportSaveDialog, 'PS' ]  ],	
						[ 'command', 'CSV', -command => [ \&ExportSaveDialog, 'CSV' ]  ],																																							
					]																											
				],				
				[ 'cascade', 'Export All Pedigrees ...', -tearoff => 0, -menuitems =>
					[
						[ 'command', 'PDF', -command => [ \&BatchExport,  'PDF' ]  ],
						[ 'command', 'SVG', -command => [ \&BatchExport,  'SVG' ]  ],								
						[ 'command', 'PNG', -command => [ \&BatchExport,  'PNG' ]  ],
						[ 'command', 'POSTSCRIPT', -command => [ \&BatchExport, 'PS' ]  ],
						[ 'command', 'CSV', -command => [ \&ExportSaveDialog, 'CSV', 1 ]  ],						
					],																				
				],			
				'-',
				[ 'cascade', 'Encoding ...', -tearoff => 0, -menuitems => 
					[
						[ 'radiobutton', 'ASCII' ,  -value => 'ascii', -variable => \$param->{ENCODING} ],
						[ 'radiobutton', 'UTF-8' , -value => 'utf8', -variable => \$param->{ENCODING} ],
						[ 'radiobutton', 'UTF-16LE' , -value => 'utf16le', -variable => \$param->{ENCODING} ],
					]
				],
				[ 'checkbutton', ' Write BOM' , -variable => \$param->{WRITE_BOM} ],
				'-',
				[ 'command', 'Page Settings ...', -command => \&OptionsPrint,   ],
				'-',
				[ 'command', 'Clear all',	-command => [ \&Clear, 'all' ]],
				[ 'command', 'Clear current',	-command => [ \&Clear, 'curr' ]],
				'-',
				[ 'command', 'Exit',	-command => sub { exit } ],
			]
		],
		[ '~Edit',
			[
				['command', 'Zoom In', 		-command => [ \&Zoom,  1 ] , -accelerator => '+'],
				['command', 'Zoom Out', 	-command => [ \&Zoom, -1 ] , -accelerator => '-'],
				'-',
				['command', 'Center View', 	-command => [ \&AdjustView ], -accelerator => 'F7' ],
				['command', 'Fit View', 	-command => [ \&AdjustView, -fit => 'center' ], -accelerator => 'F8' ],
				'-',
				['command', 'Redraw Ped', -command => \&RedrawPedForce , -accelerator => 'F5'],
				['command', 'Shuffle Haplotype Colors', -command => \&ReSetHaploShuffle , -accelerator => 'F6'],
				'-',
				['command', 'New Pedigree',	-command => \&NewPedigree,  -accelerator => 'Contr+N' ],
				['command', 'Delete Individual', -command => \&DeleteSID , -accelerator => 'Contr+D' ],
				['command', 'Add Siblings', -command => \&AddSiblings , -accelerator => 'Contr+I' ],
				['command', 'Add Parents', -command => \&AddParents  ],
				['command', 'Add Mate & Offspring', -command => \&AddMateAndOffspring  ],
				['command', 'Set/Unset Consanguinity', -command => \&SetAsConsanguine  ],
				['cascade', 'Set/Unset Twins ...', -tearoff => 0,	-menuitems =>
					[
						['command', 'monozygotic',-command => [ \&SetAsTwins, 'm' ], ],
						['command', 'dizygotic',	-command => [ \&SetAsTwins, 'd' ], ]
					]
				],
				'-',
				[ 'checkbutton', ' Show Grid' , -variable => \$param->{SHOW_GRID} , -command => \&ShowGrid ]
			]
		],
		[ '~View',
			[
				[ 'cascade', 'Draw Pedigree ...' , -tearoff => 1 ],
			]
		],
		[ '~Options',
			[
				[ 'command', 'Configuration ...', 	-command => \&Configuration , -accelerator => 'Contr+F' ],
				[ 'command', 'Breaking Loops ...',		-command => \&OptionsLoopBreak  ],
				[ 'command', 'Cansanguinity Settings ...', -command => \&OptionsConsanguine  ], 
				[ 'command', 'Page Settings ...', -command => \&OptionsPrint  ],
				'-',
				[ 'checkbutton', 'Sort by SID' , -variable => \$param->{SORT_BY_PEDID} ],	
				[ 'checkbutton', 'Sort couples by gender' , -variable => \$param->{SORT_COUPLE_BY_GENDER} ],	
										
			]
		],
		[ '~Help',
			[
				[ 'command', 'About HaploPainter ...', 	-command => \&ShowAbout ],
			]
		],
	]
}

# some needful functions are chosable via post menu ( right mouse click )
#=================
sub _ContextMenu {
#=================
	[
		['command', 'Zoom In', 	-command => [ \&Zoom,  1, 1 ], -accelerator => '+' ],
		['command', 'Zoom Out', -command => [ \&Zoom, -1, 1 ], -accelerator => '-' ],
		,'-',
		['command', 'New Pedigree',	-command => \&NewPedigree , -accelerator => 'Contr+N'],
		['command', 'Delete Individual', -command => \&DeleteSID , -accelerator => 'Contr+D' ],
		['command', 'Add Siblings', -command => \&AddSiblings , -accelerator => 'Contr+I' ],
		['command', 'Add Parents', -command => \&AddParents  ],
		['command', 'Add Mate & Offspring', -command => \&AddMateAndOffspring  ],
		['command', 'Set/Unset Consanguinity', -command => \&SetAsConsanguine  ],
		['cascade', 'Set/Unset Twins ...', -tearoff => 0,	-menuitems =>
			[
				['command', 'monozygotic',-command => [ \&SetAsTwins, 'm' ], ],
				['command', 'dizygotic',	-command => [ \&SetAsTwins, 'd' ], ]
			]
		],
		,'-',
		['command', 'Center View', -command => [ \&AdjustView ], -accelerator => 'F7' ],
		['command', 'Fit View', -command => [ \&AdjustView, -fit => 'center' ], -accelerator => 'F8' ],
		,'-',
		[ 'command', 'Configuration ...', 	-command => \&Configuration , -accelerator => 'Contr+F' ],
		[ 'command', 'Breaking Loops ...',		-command => \&OptionsLoopBreak  ],
		[ 'command', 'Cansanguinity Settings ...', -command => \&OptionsConsanguine  ], 
		[ 'command', 'Page Settings ...', -command => \&OptionsPrint,   ],		
		,'-',
		[ 'checkbutton', ' Show Grid' , -variable => \$param->{SHOW_GRID} , -command => \&ShowGrid ]
	]
}

## attaches a new core family
#================
sub NewPedigree {
#================
	
	my $d = $mw->DialogBox(-title => 'Add new family',-buttons => ['Ok', 'Cancel']);
	my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both', -anchor => 'w');
	my $fam_new;
	$f1->Label(-text => 'Family ID')->grid(-row => 0, -column => 0, -sticky => 'e');
	$f1->Entry(-textvariable => \$fam_new, -width => 20,
	)->grid(-row => 0, -column =>1, -sticky => 'w');
		                                                  
	$d->Show eq 'Ok' || return;
	return if ! $fam_new;
	return if $self->{FAM}{PED_ORG}{$fam_new};
	$self->{GLOB}{CURR_FAM} = $fam_new;
	$self->{GLOB}{FILENAME} = "new_pedfile.hp" if !$self->{GLOB}{FILENAME};
	
	AddFamToSelf($fam_new);
	push @ { $self->{FAM}{PED_ORG}{$fam_new} }, ([1,0,0,1,1],[2,0,0,2,1],[3,1,2,1,1]);
	ProcessFamily($fam_new);
		
	my $fileref = $menubar->entrycget('View', -menu);
	my $drawref = $fileref->entrycget('Draw Pedigree ...', -menu);	
	
	$drawref->add('command', -label => $fam_new, -command => sub {
		StoreDrawPositions();
		DrawOrRedraw($fam_new);
		RestoreDrawPositions()
	});	
  DoIt();
}


#=================
sub OpenDefaults {
#=================
	return unless $self->{GLOB}{CURR_FAM};
	my $file = $mw->getOpenFile(-filetypes		=> [[ 'All Files',	 '*' ],[ 'HaploPainter Files', 'hp' ]]) or return undef;
	my $test; eval { $test = retrieve($file) };
	if ($@) { ShowInfo("Error reading file $file!\n$@", 'warning'); return undef}
	@_ = nsort keys % { $test->{FAM}{PED_ORG} };
	if (!@_) {  ShowInfo("The file seemes not to contain valid data!\n$@", 'warning'); return undef }
	
	my $family = $_[0];
	my $var;
	if (scalar @_ > 1) {
		my $d = $mw->DialogBox(-title => 'Choose family',-buttons => ['Ok', 'Cancel']);
		my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both', -anchor => 'w');
		
		$f1->Label(-text => 'Family')->grid(-row => 0, -column => 0, -sticky => 'e');
		$f1->BrowseEntry(-textvariable => \$family, -width => 20,-choices => [ @_ ]
		)->grid(-row => 0, -column =>1, -sticky => 'w');
		$f1->Checkbutton(-text => 'Import for all families', -variable => \$var)->grid(-row => 0, -column =>2, -padx => 5, -sticky => 'w');		
				                                                  
		$d->Show eq 'Ok' || return;
	}
		
	my @fam = ($self->{GLOB}{CURR_FAM});
	if ($var) { @fam = keys % { $self->{FAM}{PED_ORG} } }
	foreach my $fam (@fam) {
		foreach my $k (keys % { $def->{FAM} }) {
			if (ref $def->{FAM}{$k}) {
				foreach my $k2 (keys % { $def->{FAM}{$k} }) {
					$self->{FAM}{$k}{$fam}{$k2} = $test->{FAM}{$k}{$family}{$k2}					
				}					
			}
			else { $self->{FAM}{$k}{$fam} = $test->{FAM}{$k}{$family} }				
		}	
	}
	RedrawPedForce();	
}


### batch mode allows converting pedigrees without use of GUI in a shell environment
### Tk and GTK+ must be present anyway (as librarys and perl bindings)
#=====================
sub ExecuteBatchMode {
#=====================
	
	my %pok = qw(-pedfile 1 -pedformat 1 -outfile 1 -outformat 1 -hapfile 1 -hapformat 1 -mapfile 1 -mapformat 1 -family 1 
	-resolution 1 -paper 1 -orientation 1 -border 1 -bgcolor 1 -dbtype 1 -dbport 1 -dbsid 1 -dbhost 1 -dbtable 1 -dbuname 1 
	-dbpasswd 1 -breakloop 1 -sortbyid 1 -sortbygender 1);
	@_ = nsort keys %pok;
	
	
	if ($ARGV[0] && $ARGV[0] eq '-h') {
		print "Supported parameters: @_\n"; exit
	}
	
	if (!@ARGV || $ARGV[0] ne '-b' || scalar @ARGV < 2) { return undef }
	### set batch mode
	
	my ($pedformat) = ('linkage');
	
	$batch = 1;
	shift @ARGV;
	$_ =  scalar @ARGV/2;
	if (/\./) {
		print "Error in expected number of arguments!\n"; exit
	}
	my %arg = @ARGV;
	
	### check allowed parameters
	
	foreach (keys %arg) { if (!$pok{$_}) { print "Unknown parameter $_\nAllowed values are: (@_)"; exit }}
	
	if (!$arg{-family}) { print "Need family (-family)!\n"; exit }
	
	
	### resolution
	if ($arg{-resolution}) {
		if ( ($arg{-resolution} !~ /^\d{2,4}$/) ||  ($arg{-resolution} > 4800)  ) { print "Not allowed values for resolution (10-4800)"; exit }
		$self->{GLOB}{RESOLUTION_DPI} = $arg{-resolution};
	}
	
	### paper
	if ($arg{-paper}) {
		@_ = nsort keys % { $param->{PAPER_SIZE} };
		if (! $param->{PAPER_SIZE}{$arg{-paper}}) { print "Paper size $arg{-paper} is unknown - must be (@_)"; exit }
		$self->{GLOB}{PAPER} = $arg{-paper};
	}
	
	### orientation
	if ($arg{-orientation}) {
		if ( ($arg{-orientation} !~ /^landscape$/i) && ($arg{-orientation} !~ /^portrait$/i)) { print "Orientation $arg{-orientation} is unknown - must be landscape or portrait"; exit }
		$self->{GLOB}{ORIENTATION} = $arg{-orientation};
	}
	
	### border 
	if ($arg{-border}) {
		if ( ($arg{-border} !~ /^\d{1,3}$/) ) { print "Not allowed values for border (1-999)"; exit }
		$self->{GLOB}{BORDER} = $arg{-border};
	}
	
	### breaking loops
	if (defined $arg{-breakloop} && (($arg{-breakloop} eq '0') || ($arg{-breakloop} eq '2')) ) {
		$def->{FAM}{LOOP_BREAK_STATUS} = $arg{-breakloop}
	}
	
	### sort by id or gender
	if ($arg{-sortbyid}) {$param->{SORT_BY_PEDID} = $arg{-sortbyid}}
	if ($arg{-sortbygender}) {$param->{SORT_COUPLE_BY_GENDER} = $arg{-sortbygender}}

	### read in pedfile
	if ($arg{-pedfile} && -f $arg{-pedfile}) { 
		if ($arg{-pedformat} && $param->{PEDEGREE_FORMATS}{lc $arg{-pedformat}}) { $pedformat = lc $arg{-pedformat} }
				
		ReadPed(-file => $arg{-pedfile}, -format => uc $pedformat) or die "ReadPed";
		
		if (!$self->{FAM}{PED_ORG}{$arg{-family}}) { print "Family $arg{-family} is unknown!\n"; exit }
		$self->{GLOB}{CURR_FAM} = $arg{-family};	
		
		LoopBreak() or die "Loop";
		FindTop() or die "FindTop";	
		BuildStruk() or die "BuildStruk";		
		DrawPed() or die "DrawPed";
		
	}
	### case data base connection
	elsif ($arg{-dbtype} || $arg{-dbhost} || $arg{-dbsid}) {
		$self->{GLOB}{DB_TYPE} = $arg{-dbtype};
		
		if (! $arg{-dbport} || $arg{-dbport} !~ /^\d{3,5}$/) { print "Data base port is missing or invalid (-dbport)"; exit }
		$self->{GLOB}{DB_PORT} = $arg{-dbport};
		
		if (! $arg{-dbsid} ) { print "Data base name or SID is missing (-dbsid)"; exit }
		$self->{GLOB}{DB_SID} = $arg{-dbsid};
		
		if (! $arg{-dbhost} ) { print "Data base host name or IP number is missing (-dbhost)"; exit }
		$self->{GLOB}{DB_HOST} = $arg{-dbhost};
		
		if (! $arg{-dbtable} ) { print "Data base table name is missing (-dbtable)"; exit }
		$self->{GLOB}{DB_RELATION} = $arg{-dbtable};
		
		if (! $arg{-dbuname} ) { print "Data base user name/login name is missing (-dbuname)"; exit }
		$self->{GLOB}{DB_UNAME} = $arg{-dbuname};
		
		if (! $arg{-dbpasswd} ) { print "Data base password is missing (-dbpasswd)"; exit }
		$self->{GLOB}{DB_PASSWD} = $arg{-dbpasswd};
		
		my ($dbh, $colnames) = MakeDBConnection() or exit;
		$self->{GLOB}{CURR_FAM} = $arg{-family};	
		ReadPedFromDB($dbh,$arg{-family},$colnames->[0]) or exit;
		
		LoopBreak() or die "Loop";
		FindTop() or die "FindTop";	
		BuildStruk() or die "BuildStruk";		
		DrawPed() or die "DrawPed";		
	}
	else { print "Need pedfile (-pedfile) or database connection (-dbtype, -dbport, -dbsid, -dbhost, -dbtable, -dbuname, -dbpasswd)!\n"; exit }	
	
	### background color 
	if ($arg{-bgcolor}) {
		if ( ($arg{-bgcolor} !~ /^\#[0-9a-f]{6}$/) ) { print "Not allowed format for color - example is '#ffc000'"; exit }
		$self->{GLOB}{BACKGROUND} = $arg{-bgcolor};
		$self->{FAM}{EXPORT_BACKGROUND}{$arg{-family}} = 1;
	}
	
	if (!$arg{-outfile}) { print "Need output file (-outfile)!\n"; exit }
	if (!$arg{-outformat}) { print "Need output format!\n"; exit }
	if (!$param->{EXPORT_FORMATS}{uc $arg{-outformat}}) { print "Unknown output format $arg{-outformat}!\n" }
	
	if ($arg{-hapfile}) {
		if (! -f $arg{-hapfile}) { print "Could not open file $arg{-hapfile}!\n"; exit }
		if (! $arg{-hapformat}) { print "Need haplotype format (-hapformat)!\n"; exit }
		if (! $param->{HAPLOTYPE_FORMATS}{lc $arg{-hapformat}}) { print "Unknown haplotype format - $arg{-hapformat} -!\n" }
		ReadHaplo(-file => $arg{-hapfile}, -format => uc $arg{-hapformat}) or die "ReadHaplo"; 
		DuplicateHaplotypes() or die "DuplHap";
	}
	
	if ($arg{-mapfile}) {
		 if (! -f $arg{-mapfile}) { print "Could not open file $arg{-mapfile}!\n"; exit }
		 if (! $arg{-mapformat}) { print "Need map format (-mapformat)!\n"; exit }
		 if (! $param->{MAP_FORMATS}{lc $arg{-mapformat}}) { print "Unknown map format $arg{-mapformat}!\n" }
		 ReadMap(-file => $arg{-mapfile}, -format => $arg{-mapformat}) or die "ReadMap"; 
		 SetSymbols();	
		 RedrawPed();
	}

	DrawOrExportCanvas(-modus => uc $arg{-outformat}, -fam => $arg{-family}, -file => $arg{-outfile}) or die "DrawOrExpo";
}

#=================
sub EvalOpenFile {
#=================
	$_ = shift @_ or return;
	if (! RestoreSelf($_)) { 
		$mw->update();
		ImportPedfile ('CSV', $_);
	}	
}

#==========
sub Clear {
#==========
	$_ = shift @_;
	my $fileref = $menubar->entrycget('View', -menu);
	my $drawref = $fileref->entrycget('Draw Pedigree ...', -menu);
	$drawref->delete(0,'end');
	$canvas->delete('all');
	if ($_ eq 'all') { 
		undef $self->{FAM}; 
		foreach (qw/CURR_FAM FILENAME FILENAME_SAVE/) { undef $self->{GLOB}{$_} }
	}
	elsif ($_ eq 'curr') {
		my $fam = $self->{GLOB}{CURR_FAM} or return;
		foreach (keys % { $self->{FAM} } ) { delete $self->{FAM}{$_}{$fam} }
		for my $fam (nsort keys % { $self->{FAM}{PED_ORG} }) { 
			$drawref->add('command', -label => $fam, -command => sub {DrawOrRedraw($fam)} ) 
		}
		($self->{GLOB}{CURR_FAM}) = nsort keys % { $self->{FAM}{PED_ORG} };
		return unless $self->{GLOB}{CURR_FAM};
		StoreDrawPositions();
		DrawOrRedraw($self->{GLOB}{CURR_FAM});
		RestoreDrawPositions();
	}	
}

#==============
sub DeleteSID {
#==============
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my @act_sym = keys % { $self->{GLOB}{ACTIVE_SYMBOLS} } or return;
	my $flag;
	foreach my $sym (@act_sym) {
		(my $p) = $sym =~ /^SYM-(.+)$/ or next;
		my $p_old = $self->{FAM}{CASE_INFO}{$fam}{PID}{$p}{Case_Info_1} or next;
		
		foreach my $r (@ { $self->{FAM}{PED_ORG}{$fam} }) {
			if ($r && $r->[0] eq $p_old) {
				$flag = 1;undef $r;
				
				### mark children as founder
				foreach my $child_id (keys % { $self->{FAM}{CHILDREN}{$fam}{$p} }) {						
					my $child_old = $self->{FAM}{CASE_INFO}{$fam}{PID}{$child_id}{Case_Info_1} or next;
					L2:foreach my $r2 (@ { $self->{FAM}{PED_ORG}{$fam} }) {
						if ($r2 && $r2->[0] eq $child_old) {
							$r2->[1] = 0;$r2->[2] = 0;last L2
						}
					}					
				}							
			}
		}						
	}
	
	if ($flag) {		
		### remove zombie PIDs
		my %z;
		my $c=0;
		my $c2=0;
		foreach my $r (@ { $self->{FAM}{PED_ORG}{$fam} }) {
			next unless $r;
			$z{P}{$r->[0]} = 1;
			$z{R}{$r->[1]}++ if $r->[1];
			$z{R}{$r->[2]}++ if $r->[2];
		}
		foreach my $p (keys % { $z{P} }) {
			my $sid = $self->{FAM}{PID2PIDNEW}{$fam}{$p};
			if (! $z{R}{$p} && $self->{FAM}{FOUNDER}{$fam}{$sid}) {
				foreach my $r (@ { $self->{FAM}{PED_ORG}{$fam} }) {
					if ($r && $r->[0] eq $p) { undef $r }
				}	
			}
		}
		### count individuals and left non-founder
		foreach my $r (@ { $self->{FAM}{PED_ORG}{$fam} }) {
			next unless $r;
			$c++; 
			$c2++ if $r->[1];
		}	
		### remove family if individuals are lower then 3 or all left are non-founder
		if ( ($c<3) || !$c2 ) { Clear('curr') }
		else { RedrawPedForce() }
	}
}

#=====================
sub ExportSaveDialog {
#=====================
	my ($format, $flag) = @_;
	my $fam = $self->{GLOB}{CURR_FAM};
	my $filename = "family-$fam." . lc($format);
	if ($format eq 'CSV') {
		if ($flag) { $filename = "hpcsv.$param->{ENCODING}" }
		else { $filename = "hpcsv_family-$fam.$param->{ENCODING}" }
	}
	my $file = $mw->getSaveFile(-initialfile => $filename) or return;
	DrawOrExportCanvas(-modus => $format, -fam => $fam, -file => $file, -fammode => $flag);
}

#===============
sub SetAsTwins {
#===============
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my $tt = shift @_ ;
	my $ci = $self->{FAM}{CASE_INFO}{$fam};	
	my (%t,@sibs);
	my @act_sym = keys % { $self->{GLOB}{ACTIVE_SYMBOLS} } or return;
	return if scalar @act_sym == 1;        
	
	### are sibs already in twingroups?
	foreach (@act_sym) {
		(my $sib) = $_ =~ /^SYM-(.+)$/ or return;
		push @sibs, $sib; 	
		if ($self->{FAM}{SID2TWIN_GROUP}{$fam}{$sib}) {
			$t{$self->{FAM}{SID2TWIN_GROUP}{$fam}{$sib}}=1			
		}		
	}
	
	### unset twin groups
	if (keys %t) {
		foreach my $twin_group (keys %t) {
			@_ = keys % {$self->{FAM}{TWIN_GROUP2SID}{$fam}{$twin_group}};
			foreach my $sib (@_) { 
				delete $self->{FAM}{SID2TWIN_GROUP}{$fam}{$sib};
				delete $self->{FAM}{SID2TWIN_TYPE}{$fam}{$sib};
				my $sib_old = $ci->{PID}{$sib}{Case_Info_1};
				foreach (@ { $self->{FAM}{PED_ORG}{$fam} }) { undef @$_[9] if @$_[0] eq $sib_old }
			}
			delete $self->{FAM}{TWIN_GROUP2SID}{$fam}{$twin_group};
		}	
	}
	
	### set twin group
	else {
		my ($par, $gender);
		foreach my $sib (@sibs) {
			my $sib_old = $ci->{PID}{$sib}{Case_Info_1};	
			if (! $self->{FAM}{SID2FATHER}{$fam}{$sib}) {
				ShowInfo("The twin individual $sib_old must not be a founder.",'warning'); return undef
			}
			$par = $self->{FAM}{SID2FATHER}{$fam}{$sib} . '==' .  $self->{FAM}{SID2MOTHER}{$fam}{$sib} if ! $par;
			$gender = $self->{FAM}{SID2SEX}{$fam}{$sib} if ! $gender;
			
			### twins should be siblings
			if (! $self->{FAM}{SIBS}{$fam}{$par}{$sib}) {
				ShowInfo("The twin individual $sib_old is not a member of the sibling group.",'warning'); return undef;
			}
			### monozygotic twins schould have same gender
			if (( $tt eq 'm') && $self->{FAM}{SID2SEX}{$fam}{$sib} != $gender) {
				ShowInfo("The twin individual $sib_old is declared as monozygotic but differs in gender of other twins.", 'warning'); return undef
			}				
		}
		
		### create sib group ID
		my $tg = $tt . '_' . time;
		foreach my $sib (@sibs) {
			my $sib_old = $ci->{PID}{$sib}{Case_Info_1};	
			$self->{FAM}{SID2TWIN_GROUP}{$fam}{$sib} = $tg;     
			$self->{FAM}{SID2TWIN_TYPE}{$fam}{$sib} = $tt;      
			$self->{FAM}{TWIN_GROUP2SID}{$fam}{$tg}{$sib} = 1;
			foreach (@ { $self->{FAM}{PED_ORG}{$fam} }) { 
				@$_[9] = $tg if @$_[0] eq $sib_old 
			}
		}		
	}
	RedrawPed();
}


#=====================
sub SetAsConsanguine {
#=====================
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	
	my @act_sym = keys % { $self->{GLOB}{ACTIVE_SYMBOLS} } or return;
	return if scalar @act_sym != 2;
	
	(my $p1) = $act_sym[0] =~ /^SYM-(.+)$/ or return;
	(my $p2) = $act_sym[1] =~ /^SYM-(.+)$/ or return;
	
	my $ci = $self->{FAM}{CASE_INFO}{$fam};	
	my $p1_old = $ci->{PID}{$p1}{Case_Info_1};
	my $p2_old = $ci->{PID}{$p2}{Case_Info_1};
	
	if (! $self->{FAM}{COUPLE}{$fam}{$p1} || ! $self->{FAM}{COUPLE}{$fam}{$p1}{$p2}) {
		ShowInfo("The individuals you selected are no couples!",'warning'); return	
	}
	
	if ($self->{FAM}{CONSANGUINE_MAN}{$fam}{$p1}{$p2} ) {
		delete $self->{FAM}{CONSANGUINE_MAN}{$fam}{$p1}{$p2};
		delete $self->{FAM}{CONSANGUINE_MAN}{$fam}{$p2}{$p1};
		foreach (@ { $self->{FAM}{PED_ORG}{$fam} }) { 
			if ( (@$_[0] eq $p1_old) || (@$_[0] eq $p2_old) ) {	undef @$_[10] }
		}
		
	}
	else {
		my $tg = time;
		$self->{FAM}{CONSANGUINE_MAN}{$fam}{$p1}{$p2} = 1;
		$self->{FAM}{CONSANGUINE_MAN}{$fam}{$p2}{$p1} = 1;	
		foreach (@ { $self->{FAM}{PED_ORG}{$fam} }) { 
			if ( (@$_[0] eq $p1_old) || (@$_[0] eq $p2_old)) {	@$_[10] = $tg }
		}
	}
	RedrawPed()
}


#===============
sub AddParents {
#===============
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	
	my @act_sym = keys % { $self->{GLOB}{ACTIVE_SYMBOLS} } or return;
	return if scalar @act_sym > 1;
	(my $p) = $act_sym[0] =~ /^SYM-(.+)$/ or return;	
	$p = $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p} if $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p};
	
	my $p_old = $self->{FAM}{CASE_INFO}{$fam}{PID}{$p}{Case_Info_1} or return;
	return if ! $self->{FAM}{FOUNDER}{$fam}{$p};
	
	my ($f, $m);
	
	my $d = $mw->DialogBox(-title => 'Add parents',-buttons => ['Ok', 'Cancel']);
	my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both', -anchor => 'w');
	
	$f1->Label(-text => 'Name of father')->grid(-row => 0, -column => 0, -sticky => 'e');
	$f1->Entry(-textvariable => \$f, -width => 20,
	)->grid(-row => 0, -column =>1, -sticky => 'w');
	
	$f1->Label(-text => 'Name of mother')->grid(-row => 1, -column => 0, -sticky => 'e');
	$f1->Entry(-textvariable => \$m, -width => 20,
	)->grid(-row => 1, -column =>1, -sticky => 'w');
			                                                  
	$d->Show eq 'Ok' || return;
	
	if ($m eq $f) { ShowInfo("Mates must not have identical names!",'warning'); return undef }
	
	for ($m, $f) { 
		unless ($_) { ShowInfo("Empty fields are not allowed!",'warning'); return undef }
	}
	
	push @ { $self->{FAM}{PED_ORG}{$fam} }, [ $f, 0, 0, 1, 1 ] if ! $self->{FAM}{PID2PIDNEW}{$fam}{$f};
	push @ { $self->{FAM}{PED_ORG}{$fam} }, [ $m, 0, 0, 2, 1 ] if ! $self->{FAM}{PID2PIDNEW}{$fam}{$m};
	
	foreach my $l (@ { $self->{FAM}{PED_ORG}{$fam} }) {
		if (@$l[0] eq $p_old) {
			$l->[1] = $f;
			$l->[2] = $m;
		}
	} 	
	RedrawPedForce();		
}

#========================
sub AddMateAndOffspring {
#========================
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	
	my @act_sym = keys % { $self->{GLOB}{ACTIVE_SYMBOLS} } or return;
	return if scalar @act_sym > 1;
	(my $p) = $act_sym[0] =~ /^SYM-(.+)$/ or return;
	
	$p = $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p} if $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p};

	my $pid_old = $self->{FAM}{CASE_INFO}{$fam}{PID}{$p}{Case_Info_1} or return;
	my $sex_p = $self->{FAM}{SID2SEX}{$fam}{$p};
	if ( ($sex_p ne 1) && ($sex_p ne 2)) {
		ShowInfo("Individuals with unknown gender are not accepted!",'warning'); return undef
	}
	
	my $d = $mw->DialogBox(-title => 'Add mate and offspring',-buttons => ['Ok', 'Cancel']);
	my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both', -anchor => 'w');
	
	my ($mate, $child,$gender) = ('','', 0);
	
	$f1->Label(-text => 'Name of mate')->grid(-row => 0, -column => 0, -sticky => 'e');
	$f1->Entry(-textvariable => \$mate, -width => 20,
	)->grid(-row => 0, -column =>1, -sticky => 'w');
	
	$f1->Label(-text => 'Name of offspring')->grid(-row => 1, -column => 0, -sticky => 'e');
	$f1->Entry(-textvariable => \$child, -width => 20
	)->grid(-row => 1, -column => 1, -sticky => 'w');
	
			                                                  
	$d->Show eq 'Ok' || return;
	
	if ($mate eq $child) { ShowInfo("Mate and offspring must not have identical names!",'warning'); return undef }
	
	for ($mate, $child) { 
		unless ($_) { ShowInfo("Empty fields are not allowed!",'warning'); return undef }	
	}
	
	if ($self->{FAM}{PID2PIDNEW}{$fam}{$child}) {
		ShowInfo("You already used the child ID in this pedigree!",'warning'); return undef
	}		
	
	if ($self->{FAM}{PID2PIDNEW}{$fam}{$mate}) {
		my $pid_mate_new = $self->{FAM}{PID2PIDNEW}{$fam}{$mate};
		
		
		if ($self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$pid_mate_new}) {
			$pid_mate_new = $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$pid_mate_new};
			$mate =  $self->{FAM}{CASE_INFO}{$fam}{PID}{$pid_mate_new}{Case_Info_1};
		}
		
		my $sex_mate = $self->{FAM}{SID2SEX}{$fam}{$pid_mate_new};
		if (!$sex_mate or ($sex_mate == $sex_p)) {
			ShowInfo("Gender of mate does not match necessary criteria!",'warning'); return undef
		}
	}
	
	if ($sex_p == 1) {
		push @ { $self->{FAM}{PED_ORG}{$fam} }, [ $mate, 0, 0, 2, 1 ] if ! $self->{FAM}{PID2PIDNEW}{$fam}{$mate}; 
		push @ { $self->{FAM}{PED_ORG}{$fam} }, [ $child, $pid_old, $mate, 0, 1 ];
	}
	else {
		push @ { $self->{FAM}{PED_ORG}{$fam} }, [ $mate, 0, 0, 1, 1 ] if ! $self->{FAM}{PID2PIDNEW}{$fam}{$mate};
		push @ { $self->{FAM}{PED_ORG}{$fam} }, [ $child, $mate, $pid_old, 0, 1 ];
	}	
	
	RedrawPedForce();	
}


### dialog to attach multiple sibs 
#================
sub AddSiblings {
#================
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	
	my @act_sym = keys % { $self->{GLOB}{ACTIVE_SYMBOLS} } or return;
	return if scalar @act_sym > 1;
	(my $p) = $act_sym[0] =~ /^SYM-(.+)$/ or return;
	$p = $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p} if $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p};
	
	return if $self->{FAM}{FOUNDER}{$fam}{$p};
	
	my $f = $self->{FAM}{SID2FATHER}{$fam}{$p};
	my $f_old = $self->{FAM}{CASE_INFO}{$fam}{PID}{$f}{Case_Info_1} or return;
	
	my $m = $self->{FAM}{SID2MOTHER}{$fam}{$p};
	my $m_old = $self->{FAM}{CASE_INFO}{$fam}{PID}{$m}{Case_Info_1} or return;
	
	my $pid_new = {};
	
	my $d = $mw->DialogBox(-title => 'Add siblings',-buttons => ['Ok', 'Cancel']);
	my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both', -anchor => 'w');
	
	my $gender;
	for (1 ..8) {
		$pid_new->{$_}{GENDER} = 1;
		$f1->Label(-text => "Name of sibling #$_")->grid(-row => $_-1, -column => 0, -sticky => 'e');
		$f1->Entry(-textvariable => \$pid_new->{$_}{NAME}, -width => 20,
		)->grid(-row => $_-1, -column =>2, -sticky => 'w');
		
		$f1->Radiobutton(-value => 1 ,-variable =>\$pid_new->{$_}{GENDER},-text => 'male')->grid(-row => $_-1, -column => 3, -sticky => 'w');
		$f1->Radiobutton(-value => 2 ,-variable =>\$pid_new->{$_}{GENDER},-text => 'female')->grid(-row => $_-1, -column => 4, -sticky => 'w');
		$f1->Radiobutton(-value => 0 ,-variable =>\$pid_new->{$_}{GENDER},-text => 'unknown gender')->grid(-row => $_-1, -column => 5, -sticky => 'w');		
	}
		                                                  
	$d->Show eq 'Ok' || return;
	
	my $flag;
	for (1..8) {
		if ($pid_new->{$_}{NAME}) {
			my $name = $pid_new->{$_}{NAME};
			if ($self->{FAM}{PID2PIDNEW}{$fam}{$name}) {
		 		ShowInfo("The PID $name is already in use, pleasy try again!", 'error'); return  
			}
			push @ { $self->{FAM}{PED_ORG}{$fam} }, [ $name, $f_old, $m_old, $pid_new->{$_}{GENDER}, 1 ];
			$flag = 1
		}
	}
	
  RedrawPedForce() if $flag;
}


# MakeSelfGlobal is called once to copy the defaults into $self
# It holds object orientated all subvariables in one hash. 
# The structure is saved later by Storable.pm
#===================
sub MakeSelfGlobal {
#===================
	## copy up to three hash levels from $def to $self
	foreach my $k1 (keys % { $def->{GLOB} }) {
		if (ref $def->{GLOB}{$k1}) { 
			foreach my $k2 (keys % { $def->{GLOB}{$k1} }) {
				if (ref $def->{GLOB}{$k1}{$k2}) { 
					foreach my $k3 (keys % { $def->{GLOB}{$k1}{$k2} }) {					
						$self->{GLOB}{$k1}{$k2}{$k3} = $def->{GLOB}{$k1}{$k2}{$k3}
					}
				}
				else { $self->{GLOB}{$k1}{$k2} = $def->{GLOB}{$k1}{$k2} }	
			}			
		}
		else { $self->{GLOB}{$k1} = $def->{GLOB}{$k1} }	
	} 
}

### copy defaults for given family
#=================
sub AddFamToSelf {
#=================
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	unless ($fam) { ShowInfo("Achtung : Argumentfehler in Funktion AddFammToSelf ", 'error'); return }
	## copy up to three hash levels from $def to $self
	foreach my $k1 (keys % { $def->{FAM} }) {
		if (ref $def->{FAM}{$k1}) { 
			foreach my $k2 (keys % { $def->{FAM}{$k1} }) {
				if (ref $def->{FAM}{$k1}{$k2}) { 
					foreach my $k3 (keys % { $def->{FAM}{$k1}{$k2} }) {					
						$self->{FAM}{$k1}{$fam}{$k2}{$k3} = $def->{FAM}{$k1}{$k2}{$k3}
					}
				}
				else { $self->{FAM}{$k1}{$fam}{$k2} = $def->{FAM}{$k1}{$k2} }	
			}			
		}
		else { $self->{FAM}{$k1}{$fam} = $def->{FAM}{$k1} }	
	} 
}


# Show Context Menue and store current cursor coordinates 
# for later positioning after zooming
#=====================
sub ShowContextMenue {
#=====================
	my ($c, $menu, $x, $y) = @_;
	$menu->Post($mw->pointerxy); 
	$menu->grabRelease();
	$self->{GLOB}{X_SCREEN} = $x;
	$self->{GLOB}{Y_SCREEN} = $y;	
	$self->{GLOB}{X_CANVAS} = $c->canvasx($x);
	$self->{GLOB}{Y_CANVAS} = $c->canvasy($y);	
}


# double clicking uninformative alleles cause appearing dialog box to change
# chromosomal phase or declaring as uninformative
#===============
sub KlickAllel {
#===============
	return if $self->{GLOB}{STATUS};
	my $fam = $self->{GLOB}{CURR_FAM};
	@_ = $self->{GLOB}{ACTIVE_ITEM};
	foreach (@_) {
		next unless $_;
		if (/ALLEL-(\w)-(\d+)-(.+)/) {

			my $fa = $self->{FAM}{SID2FATHER}{$fam}{$3};
			my $mo = $self->{FAM}{SID2MOTHER}{$fam}{$3};

			my ($var, $P, $M, $flag);
			my $i = 0;
			my $un = $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam};

			### Paternaler Haplotyp
			if ($1 eq 'P') {
				$P = $self->{FAM}{HAPLO}{$fam}{PID}{$fa}{P}{BAR}[$2][1];
				$M = $self->{FAM}{HAPLO}{$fam}{PID}{$fa}{M}{BAR}[$2][1]
			} else {
				$P = $self->{FAM}{HAPLO}{$fam}{PID}{$mo}{P}{BAR}[$2][1];
				$M = $self->{FAM}{HAPLO}{$fam}{PID}{$mo}{M}{BAR}[$2][1]
			}

			my $d = $mw->DialogBox(-title => 'Set color of Haplotype',-buttons => ['Ok']);
			my $f = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');

			$f->Label(-width => 2, -bg =>  $P)->grid( -row => 0, -column => 0, -sticky => 'e');
			$f->Label(-width => 2, -bg =>  $M)->grid( -row => 1, -column => 0, -sticky => 'e');
			$f->Label(-width => 2, -bg => $un)->grid( -row => 2, -column => 0, -sticky => 'e');

			foreach my $l ( "Paternal", "Maternal", 'Not informative') {
				$f->Radiobutton( -text => $l, -variable => \$var,-value => $l, -command => sub {
					if ($var eq 'Paternal') {
						$self->{FAM}{HAPLO}{$fam}{PID}{$3}{$1}{BAR}[$2][1] = $P; $flag = 1;
						$self->{FAM}{HAPLO}{$fam}{PID}{$3}{$1}{BAR}[$2][0] = 'NI-3';
						
						if ($self->{FAM}{DUPLICATED_PID}{$fam}{$3}) {
							foreach my $dupl (keys % { $self->{FAM}{DUPLICATED_PID}{$fam}{$3} }) {
								$self->{FAM}{HAPLO}{$fam}{PID}{$dupl}{$1}{BAR}[$2][1] = $P; $flag = 1;
								$self->{FAM}{HAPLO}{$fam}{PID}{$dupl}{$1}{BAR}[$2][0] = 'NI-3';
							}
						}
						
					}
					elsif ($var eq 'Maternal') {
						$self->{FAM}{HAPLO}{$fam}{PID}{$3}{$1}{BAR}[$2][1] = $M; $flag = 1;
						$self->{FAM}{HAPLO}{$fam}{PID}{$3}{$1}{BAR}[$2][0] = 'NI-3';
						
						if ($self->{FAM}{DUPLICATED_PID}{$fam}{$3}) {
							foreach my $dupl (keys % { $self->{FAM}{DUPLICATED_PID}{$fam}{$3} }) {
								$self->{FAM}{HAPLO}{$fam}{PID}{$dupl}{$1}{BAR}[$2][1] = $M; $flag = 1;
								$self->{FAM}{HAPLO}{$fam}{PID}{$dupl}{$1}{BAR}[$2][0] = 'NI-3';
							}
						}
						
					} else {
						$self->{FAM}{HAPLO}{$fam}{PID}{$3}{$1}{BAR}[$2][0] = 'NI-2'; $flag = 1;
						if ($self->{FAM}{DUPLICATED_PID}{$fam}{$3}) {
							foreach my $dupl (keys % { $self->{FAM}{DUPLICATED_PID}{$fam}{$3} }) {						
								$self->{FAM}{HAPLO}{$fam}{PID}{$dupl}{$1}{BAR}[$2][0] = 'NI-2';
							}
						}
					}
				})->grid( -row => $i, -column => 1, -sticky => 'w');
				$i++
			}
			$d->Show();
			RedrawPed() if $flag;
		}
	}
}

#==============
sub KlickHead {
#==============
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my $d = $mw->DialogBox(-title => 'Change family title',-buttons => ['Ok', 'Cancel']);
	my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');			
	$f1->Label(-text => 'Title')->grid(-row => 0, -column => 0, -sticky => 'e');
	$f1->Entry(-textvariable => \$self->{FAM}{TITLE}{$fam}, -width => 20,
	)->grid(-row => 0, -column =>1, -sticky => 'w');			
	$d->Show eq 'Ok' || return;
	RedrawPed();
}

#================
sub KlickSymbol {
#================
	return if $self->{GLOB}{STATUS};
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my $backup = freeze($self);
	my ($c) = @_;
	my $ci = $self->{FAM}{CASE_INFO}{$fam}{PID};
	
	@_ = $c->itemcget('current', -tags);
	foreach my $tag (@_) {
		if ($tag =~ /SYM-(\S+)/) {
			my $id = $1;
			my $sid_old = $ci->{$id}{'Case_Info_1'};
			my $sid_old_save = $sid_old;
			my $gender = $self->{FAM}{SID2SEX}{$fam}{$id};
			
			my $d = $mw->DialogBox(-title => 'Change individual settings',-buttons => ['Ok', 'Cancel']);
			my $f0 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
			my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
			my $f2 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
			my $f3 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
			my $f4 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
			

			my ($lt1, $lt2, $lt3);
			$lt1="SID:$sid_old ";
			if ($self->{FAM}{FOUNDER}{$fam}{$id}) {$lt2 = "Father:unknown "; $lt3= "Mother:unknown " }
			else {
				
				$lt2 = "Father:$ci->{$self->{FAM}{SID2FATHER}{$fam}{$id}}{'Case_Info_1'} ";
				$lt3 = "Mother:$ci->{$self->{FAM}{SID2MOTHER}{$fam}{$id}}{'Case_Info_1'} ";
			}
			
			$f0->Label(-text => $lt1)->pack->grid(-row => 0, -column => 0, -sticky => 'w');
			$f0->Label(-text => $lt2)->pack->grid(-row => 0, -column => 1, -sticky => 'w');
			$f0->Label(-text => $lt3)->pack->grid(-row => 0, -column => 2, -sticky => 'w');
			
			$f1->Label(-text => 'Affection')->grid(-row => 0, -column => 3, -sticky => 'w');
			$f1->BrowseEntry(	-choices => [ 0..9 ], -state => 'readonly',
				-textvariable => \$self->{FAM}{SID2AFF}{$fam}{$id}, -width => 3,
			)->grid(-row => 0, -column => 2, -sticky => 'w');
			
			$f1->Checkbutton(-text => 'adopted', -variable => \$self->{FAM}{IS_ADOPTED}{$fam}{$id})->grid(-row => 0, -column => 0, -sticky => 'w');
			$f1->Checkbutton(-text => 'deceased', -variable => \$self->{FAM}{IS_DECEASED}{$fam}{$id})->grid(-row => 1, -column => 0, -sticky => 'w');
			$f1->Checkbutton(-text => 'TOP', -variable => \$self->{FAM}{IS_SAB_OR_TOP}{$fam}{$id})->grid(-row => 2, -column => 0, -sticky => 'w');
			$f1->Checkbutton(-text => 'proband', -variable => \$self->{FAM}{IS_PROBAND}{$fam}{$id})->grid(-row => 3, -column => 0, -sticky => 'w');
			                                                
			$f1->Radiobutton(-value => 0 ,-variable =>\$gender,-text => 'unknown gender')->grid(-row => 2, -column => 1, -sticky => 'w');
			$f1->Radiobutton(-value => 1 ,-variable =>\$gender,-text => 'male')->grid(-row => 0, -column => 1, -sticky => 'w');
			$f1->Radiobutton(-value => 2 ,-variable =>\$gender,-text => 'female')->grid(-row => 1, -column => 1, -sticky => 'w');
			
			$f2->Label(-text => 'Text inside symbol')->grid(-row => 0, -column => 0, -sticky => 'e');
			$f2->Entry(-textvariable => \$self->{FAM}{INNER_SYMBOL_TEXT}{$fam}{$id}, -width => 20,
			)->grid(-row => 0, -column =>1, -sticky => 'w');
			
			$f2->Label(-text => 'Text beside symbol')->grid(-row => 1, -column => 0, -sticky => 'e');
			$f2->Entry(-textvariable => \$self->{FAM}{SIDE_SYMBOL_TEXT}{$fam}{$id}, -width => 20,
			)->grid(-row => 1, -column =>1, -sticky => 'w');
			
			$f3->Label(-text => 'Case Info #1')->grid(-row => 0, -column => 0, -sticky => 'e');
			$f3->Entry(-textvariable => \$sid_old, -width => 25,
			)->grid(-row => 0, -column =>1, -sticky => 'w');
			$f3->Checkbutton(-text => 'show', -variable => \$self->{FAM}{CASE_INFO_SHOW}{$fam}{1})->grid(-row => 0, -column => 2, -sticky => 'w');
															                                                  
			for ( 1 .. 4 ) {
				my $var = 'Case_Info_' . ($_+1);
				$f4->Label(-text => 'Case Info #' .($_+1))->grid(-row => $_-1, -column => 0, -sticky => 'e');
				$f4->Entry(-textvariable => \$ci->{$id}{$var}, -width => 25,
				)->grid(-row => $_-1, -column =>1, -sticky => 'w');
				$f4->Checkbutton(-text => 'show', -variable => \$self->{FAM}{CASE_INFO_SHOW}{$fam}{$_+1})->grid(-row => $_-1, -column => 2, -sticky => 'w');
			}			
			
			$_ = $d->Show;
			
			### Pressing OK
			if ($_ eq 'Cancel') {	$self = thaw($backup) }
			elsif ($_ eq 'Ok') { 
				
				
				if (($gender ne $self->{FAM}{SID2SEX}{$fam}{$id}) && $self->{FAM}{CHILDREN}{$fam}{$id}) {
					ShowInfo("Changing gender for individuals that which have offspring is forbidden!", 'warning'); return
				}
				$self->{FAM}{SID2SEX}{$fam}{$id} = $gender;
				
				### Check if case info #1 contains data 
				if (!$sid_old) {
					ShowInfo("The Case Info #1 filed must contain data!, 'warning'"); return
				}
				### Check if change in case info #1 lead to PID duplication
				if ($sid_old ne $sid_old_save) {
					if ($self->{FAM}{PID2PIDNEW}{$fam}{$sid_old}) {
						ShowInfo("SID $sid_old is already in use!", 'warning'); return
					}
					### change --> rename PID in PED_ORG
					foreach my $l (@ {$self->{FAM}{PED_ORG}{$fam}}) {
						next unless $l;
						for (0..2) { $l->[$_] = $sid_old if $l->[$_] eq $sid_old_save }
					}
					
					my $id_save = $self->{FAM}{PID2PIDNEW}{$fam}{$sid_old_save};
					delete $self->{FAM}{PID2PIDNEW}{$fam}{$sid_old_save};
					$self->{FAM}{PID2PIDNEW}{$fam}{$sid_old} = $id_save;
					$ci->{$id}{'Case_Info_1'} = $sid_old;
				}
				
				foreach my $l (@ {$self->{FAM}{PED_ORG}{$fam}}) {
					next unless $l;
					next if $l->[0] ne $sid_old;
					$l->[3] = $self->{FAM}{SID2SEX}{$fam}{$id};
					$l->[4] = $self->{FAM}{SID2AFF}{$fam}{$id};
					$l->[5] = $self->{FAM}{IS_DECEASED}{$fam}{$id};
					$l->[6] = $self->{FAM}{IS_SAB_OR_TOP}{$fam}{$id};
					$l->[7] = $self->{FAM}{IS_PROBAND}{$fam}{$id};
					$l->[8] = $self->{FAM}{IS_ADOPTED}{$fam}{$id};
					$l->[11] = $self->{FAM}{INNER_SYMBOL_TEXT}{$fam}{$id};
					$l->[12] = $self->{FAM}{SIDE_SYMBOL_TEXT}{$fam}{$id};	
					for (2..5) {
						$l->[11+$_] = $ci->{$id}{'Case_Info_'.$_} 
					}	
					last;
				}				
				RedrawPed()
			}				
		}
	}
}


# Moving mouse over uninformative alleles from non-founder cause changing its color to red
#===============
sub EnterAllel {
#===============	
	my ($c) = @_;
	my $fam = $self->{GLOB}{CURR_FAM};
	my $z = $self->{GLOB}{ZOOM}{$fam};
		
	@_ = $c->itemcget('current', -tags);
		
	foreach my $tag (@_) {
		if ($tag =~ /ALLEL-(\w)-(\d+)-(.+)/) {
			my $fa = $self->{FAM}{SID2FATHER}{$fam}{$3};
			my $mo = $self->{FAM}{SID2MOTHER}{$fam}{$3};
			return if ! $fa || ! $mo;

			my ($a1, $a2);
			if ($1 eq 'P') {
				$a1 = $self->{FAM}{HAPLO}{$fam}{PID}{$fa}{P}{TEXT}[$2];
				$a2 = $self->{FAM}{HAPLO}{$fam}{PID}{$fa}{M}{TEXT}[$2]
			} else {
				$a1 = $self->{FAM}{HAPLO}{$fam}{PID}{$mo}{P}{TEXT}[$2];
				$a2 = $self->{FAM}{HAPLO}{$fam}{PID}{$mo}{M}{TEXT}[$2]
			}
			
			$self->{GLOB}{ACTIVE_ITEM} = $tag;
			$self->{GLOB}{ACTIVE_COLOUR} = $c->itemcget($tag, -fill);
			
			if ( (! $a1 || ! $a2) || ( $a1 == $a2 ) ) {	
				$c->itemconfigure($tag, -fill => 'red');
			}
		}
	}
}


#==================
sub HeadB1Release {
#==================
	my $c = shift;
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my $z = $self->{FAM}{ZOOM}{$fam};
	my $gx = $self->{FAM}{GITTER_X}{$fam}*$z;
	my $gy = $self->{FAM}{GITTER_Y}{$fam}*$z;	
	@_ = $c->coords('HEAD');
	my $X = $self->{FAM}{TITLE_X}{$fam} = sprintf ("%1.0f", $_[0]/$gx);
	my $Y = $self->{FAM}{TITLE_Y}{$fam} = sprintf ("%1.0f", $_[1]/$gy);
	
	RedrawPed();
}


# sub for drag and drop symbols features
#===================
sub MouseB1Release {
#===================	
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my $c = $canvas;
	my $m = $self->{FAM}{MATRIX}{$fam};
	my $s = $self->{GLOB}{ACTIVE_SYMBOLS};
	my $z = $self->{FAM}{ZOOM}{$fam};
	my $gx = $self->{FAM}{GITTER_X}{$fam}*$z;
	my $gy = $self->{FAM}{GITTER_Y}{$fam}*$z;


	if (! $self->{GLOB}{STATUS}) {
		foreach my $id (keys %$s) {
			my $p = $s->{$id}{PID};
			my ($x1g, $y1g) = ($m->{P2XY}{$p}{X}, $m->{P2XY}{$p}{Y});

			@_ = $c->coords($id);
			my ($x1c, $y1c) = ( ($_[0]+$_[2])*0.5 , ($_[1]+$_[3])*0.5 );
			@_ = $c->coords($s->{$id}{ID_CLONE}) or return;
			my ($x2c, $y2c) = ( ($_[0]+$_[2])*0.5 , ($_[1]+$_[3])*0.5 );

			my $gxd = sprintf ("%1.0f", ($x2c-$x1c)/$gx);
			my $gyd = sprintf ("%1.0f", ($y2c-$y1c)/$gy);

			my ($x2g, $y2g) = ( $x1g+$gxd, $y1g+$gyd );

			if ( $gxd || $gyd ) {
				### somebody at X/Y ?
				if ( ! $m->{YX2P}{$y2g}{$x2g}  ) {
					delete $m->{YX2P}{$y1g}{$x1g};
					$m->{YX2P}{$y2g}{$x2g} = $p;
					$m->{P2XY}{$p}{X} = $x2g;
					$m->{P2XY}{$p}{Y} = $y2g;				
				}
			}
			$c->delete($s->{$id}{ID_CLONE});
			delete $s->{$id}{ID_CLONE};
		}
		RedrawPed();
		### restore active symbols
		foreach my $id (keys %$s) { $c->itemconfigure($id, -fill => 'red') }
	}
	
	
}

# moving title 
#=============
sub MoveHead {
#=============
	my ($c, $x, $y) = @_;
	
	$x = $c->canvasx($x);
	$y = $c->canvasy($y);	
	$c->move('current',$x-$self->{GLOB}{X_CANVAS},$y-$self->{GLOB}{Y_CANVAS});
	$self->{GLOB}{X_CANVAS} = $x;
	$self->{GLOB}{Y_CANVAS} = $y;			
}

#==================
sub ButtonRelease {
#==================
	my ($c) = @_;
	
	### selection modus
	if (! $self->{GLOB}{STATUS}) {
		
		### box drawing modus
		if (! keys % { $self->{GLOB}{ACTIVE_SYMBOLS} }) {
			
			## find symbols inside the BOX area
			my (%h,@i);
			@_ = $c->coords('BOX') or return;		
			$c->delete('BOX');
			my @list = $c->find('enclosed',@_) or return;
			foreach ($c->find('withtag', 'SYMBOL')) {$h{$_} = 1 }
			foreach (@list) { push @i, $_ if $h{$_} }
			
			foreach (@i) {
				my %t; foreach my $tag ($c->gettags($_)) { $t{$_} = $tag if $tag =~ /^SYM-/ }
				$t{$_} =~ /^SYM-(.+)$/ or return;
				$self->{GLOB}{ACTIVE_SYMBOLS}{$t{$_}}{COLOR_ORG} = $c->itemcget($_, '-fill');			
				$self->{GLOB}{ACTIVE_SYMBOLS}{$t{$_}}{PID} = $1;
				$c->itemconfigure($_, -fill => 'red');			
			}
		}
		else {
			### delete all active items
			foreach ( keys % { $self->{GLOB}{ACTIVE_SYMBOLS} }) {
				$c->delete($self->{GLOB}{ACTIVE_SYMBOLS}{$_}{ID_CLONE});
				delete $self->{GLOB}{ACTIVE_SYMBOLS}{$_}{ID_CLONE};
			}
		}
	}
}

# draw stippled bounding box to select multiple symbols
#================
sub MouseB1Move {
#================
	my ($c,$x,$y) = @_;
	
	my $x1 = $self->{GLOB}{X_CANVAS};
	my $y1 = $self->{GLOB}{Y_CANVAS};					
	
	my $xs1 = $self->{GLOB}{X_SCREEN};
	my $ys1 = $self->{GLOB}{Y_SCREEN};			
	
	
	my $x2 = $c->canvasx($x);
	my $y2 = $c->canvasy($y);
		
	my $scr_x = $self->{GLOB}{X_SCROLL};
	my $scr_y = $self->{GLOB}{Y_SCROLL};
	
	### STATUS = 0 --> moving symbols
	if (! $self->{GLOB}{STATUS}) {
		my $curr_tag; foreach my $tag ($c->itemcget('current', -tags)) {
			$curr_tag = $tag if $tag =~ /^SYM-/;
		}
		### if mouse pointer is not over any symbol draw a symbol selection box
		if (! $curr_tag) {				
			$c->delete('BOX');	
			$c->createRectangle($x1,$y1,$x2,$y2, -dash => '.', -width => 1, -outline => 'grey50', -tags => [ 'BOX' ]);
		}
		
		### move active symbols arround the screen
		else {
			my @act_sym = keys % { $self->{GLOB}{ACTIVE_SYMBOLS} } or return;
			my $fam = $self->{GLOB}{CURR_FAM} or return;
			
			### clone objects if necessary    
			foreach (@act_sym) {
				if ( ! $self->{GLOB}{ACTIVE_SYMBOLS}{$_}{ID_CLONE} ) {
					my $pid = $self->{GLOB}{ACTIVE_SYMBOLS}{$_}{PID} or print "NO PID\n";									
					@_ = ($c->coords($_), -width => 1,-outline => 'white' , -fill => 'grey85' );
					my $id;
					if ($self->{FAM}{IS_SAB_OR_TOP}{$fam}{$pid} || !$self->{FAM}{SID2SEX}{$fam}{$pid}) { $id = $c->createPolygon(@_) }															
					elsif ($self->{FAM}{SID2SEX}{$fam}{$pid} == 1) { $id = $c->createRectangle(@_) }
					elsif ($self->{FAM}{SID2SEX}{$fam}{$pid} == 2) { $id = $c->createOval(@_) }  					
					$self->{GLOB}{ACTIVE_SYMBOLS}{$_}{ID_CLONE} = $id;                    
				}
			}
			
			foreach (@act_sym) {
				$c->move($self->{GLOB}{ACTIVE_SYMBOLS}{$_}{ID_CLONE},$x2-$self->{GLOB}{X_CANVAS},$y2-$self->{GLOB}{Y_CANVAS});			
			}	
			$self->{GLOB}{X_CANVAS} = $x2;
			$self->{GLOB}{Y_CANVAS} = $y2;
		}
	}
	
	### STATUS = 3 --> move canvas (hand symbol)
	elsif ($self->{GLOB}{STATUS} == 3) {
						
		my @sc = $canvas->Subwidget('canvas')->cget(-scrollregion);
		
		my @xv = $canvas->xview;
		my @yv = $canvas->yview;

		my $xvd = $xv[1]-$xv[0];
		my $yvd = $yv[1]-$yv[0];

		my $xsd = $sc[2]-$sc[0];
		my $ysd = $sc[3]-$sc[1];

		my $wx = $xsd*$xvd;
		my $wy = $ysd*$yvd;					

		my $x_diff = ($xs1-$x);
		my $y_diff = ($ys1-$y);
		
		my $prop_x = 1-$xv[1]+$xv[0];
		my $prop_y = 1-$yv[1]+$yv[0];
		
		my $versch_fx = $x_diff/($xsd-$wx);
		my $versch_fy = $y_diff/($ysd-$wy);
		
		my $moveto_x = ($prop_x*$versch_fx) + $scr_x->[0];
		my $moveto_y = ($prop_y*$versch_fy) + $scr_y->[0];
			
		$canvas->xviewMoveto($moveto_x);	
		$canvas->yviewMoveto($moveto_y);			
	}
}


#========================
sub MouseB1ControlKlick {
#========================
	my ($c, $x, $y) = @_;
	
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	
	### store mouse x/y coordinates as screen distance
	$self->{GLOB}{X_SCREEN} = $x;
	$self->{GLOB}{Y_SCREEN} = $y;
	
	$self->{GLOB}{X_CANVAS} = $c->canvasx($x);
	$self->{GLOB}{Y_CANVAS} = $c->canvasy($y);
	
	my ($curr_tag, $pid); 
	foreach my $tag ($c->itemcget('current', -tags)) {		 
		if ($tag =~ /^SYM-(.+)$/) {
			$curr_tag = $tag; $pid = $1
		}
	}
		
	if ($curr_tag && $self->{GLOB}{ACTIVE_SYMBOLS}{$curr_tag}) {
		
		my $aff = $self->{FAM}{SID2AFF}{$fam}{$pid};
		my $col = $self->{FAM}{AFF_COLOR}{$fam}{$aff};
		
		$c->itemconfigure($curr_tag, -fill => $col);
		delete $self->{GLOB}{ACTIVE_SYMBOLS}{$curr_tag};
	}
	
	elsif ($curr_tag && ! $self->{GLOB}{ACTIVE_SYMBOLS}{$curr_tag}) {
		$self->{GLOB}{ACTIVE_SYMBOLS}{$curr_tag}{PID} = $pid;
		$c->itemconfigure($curr_tag, -fill => 'red');					
	}
}

#=================
sub MouseB1Klick {
#=================
	my ($c, $x, $y) = @_;
	
	$c->Tk::focus;
	### store mouse x/y coordinates as screen distance
	$self->{GLOB}{X_SCREEN} = $x;
	$self->{GLOB}{Y_SCREEN} = $y;
	
	### store canvas x/y coordinates
	$self->{GLOB}{X_CANVAS} = $c->canvasx($x);
	$self->{GLOB}{Y_CANVAS} = $c->canvasy($y);
	
	### store scollregions 
	$self->{GLOB}{X_SCROLL} = [ $canvas->xview ];
	$self->{GLOB}{Y_SCROLL} = [ $canvas->yview ];
	
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	
	if (! $self->{GLOB}{STATUS}) {		
		my ($curr_tag, $pid); 
		foreach my $tag ($c->itemcget('current', -tags)) {
			if ($tag =~ /^SYM-(.+)$/) {
				$curr_tag = $tag;
				$pid = $1;
			}
		}
		
		if (! $curr_tag) {
			foreach (keys % { $self->{GLOB}{ACTIVE_SYMBOLS}}) {
				/^SYM-(.+)$/;
				my $aff = $self->{FAM}{SID2AFF}{$fam}{$1};
				my $col = $self->{FAM}{AFF_COLOR}{$fam}{$aff};				
				$c->itemconfigure($_, -fill => $col);
			}
			undef $self->{GLOB}{ACTIVE_SYMBOLS};
		}
		
		elsif (! $self->{GLOB}{ACTIVE_SYMBOLS}{$curr_tag}) {
			foreach (keys % { $self->{GLOB}{ACTIVE_SYMBOLS}}) {
				/^SYM-(.+)$/;
				my $col = $self->{FAM}{AFF_COLOR}{$fam}{$self->{FAM}{SID2AFF}{$fam}{$1}};				
				$c->itemconfigure($_, -fill => $col);
			}
			undef $self->{GLOB}{ACTIVE_SYMBOLS};
					
			$self->{GLOB}{ACTIVE_SYMBOLS}{$curr_tag}{PID} = $pid;
			$c->itemconfigure($curr_tag, -fill => 'red');															
		}
	}
	### STATUS = 1 --> zoom in
	elsif ($self->{GLOB}{STATUS} == 1) { Zoom($c,1,1,$x,$y) }
	
	### STATUS = 1 --> zoom in
	elsif ($self->{GLOB}{STATUS} == 2) { Zoom($c,-1,1,$x,$y) }
}

# Start drawing one pedigree
#=========
sub DoIt {
#=========					
	LoopBreak();
	FindTop() or return;	
	BuildStruk();
	DuplicateHaplotypes();
	ShuffleFounderColors();
	ProcessHaplotypes();				
	DrawPed();
	DrawOrExportCanvas();
	AdjustView(-fit => 'center');	
	1;
}

#==============
sub RedrawPed {
#==============	
	SetSymbols();	
	SetLines();	
	SetHaplo();	
	DrawOrExportCanvas() if !$batch;		
}

#===================
sub RedrawPedForce {
#===================
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	foreach my $k ( keys % { $self->{FAM} } ) {
		next if $k eq 'MAP';
		next if $k eq 'TITLE';
		undef $self->{FAM}{$k}{$fam} if ! defined $def->{FAM}{$k};
	}
	undef $self->{GLOB}{ACTIVE_SYMBOLS};
	ProcessFamily($fam) or return;
	FindLoops($fam);
	DoIt($fam);
}

#=================
sub DrawOrRedraw {
#=================
	my $fam = shift @_ or return undef;
	$self->{GLOB}{CURR_FAM} = $fam;
	undef $self->{GLOB}{ACTIVE_SYMBOLS};
	if (! $self->{FAM}{MATRIX}{$fam}) { DoIt() }
	else { RedrawPed() }	
}

#=======================
sub StoreDrawPositions {
#=======================
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	
	### Store canvas and scrollbar positions
	$self->{FAM}{CANVAS_SCROLLREGION}{$fam} = [ $canvas->Subwidget('canvas')->cget(-scrollregion) ];
	$self->{FAM}{CANVAS_XVIEW}{$fam} = [ $canvas->xview ];
	$self->{FAM}{CANVAS_YVIEW}{$fam} = [ $canvas->yview ];

}

#=========================
sub RestoreDrawPositions {
#=========================
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	return unless $self->{FAM}{CANVAS_SCROLLREGION}{$fam};
	
	### Restore canvas and scrollbar positions
	$canvas->configure(-scrollregion => $self->{FAM}{CANVAS_SCROLLREGION}{$fam});
	$canvas->xviewMoveto($self->{FAM}{CANVAS_XVIEW}{$fam}[0]);
	$canvas->yviewMoveto($self->{FAM}{CANVAS_YVIEW}{$fam}[0]);

}

#=============
sub ShowInfo {
#=============	
	my ($info, $type) = @_;
	if ($batch) { print "$info\n" }
	else {
		$mw->messageBox(
			-title => 'Status report', -message => $info,
			-type => 'OK', -icon => $type || 'info'
		)
	}
}


# This method implements maximal number of trials to find good drawing solutions
# Given values are found empirical working well. The alligning algorhithm still could be improved !
#============
sub DrawPed {
#============
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $CrossMin = 0;
	my ($save, $flag);
	my $cursor = $self->{GLOB}{CURSOR};
		
	if (! $batch) {
		$self->{GLOB}{CURSOR} = 'watch';
		$canvas->configure(-cursor => $self->{GLOB}{CURSOR});
		$canvas->update();
	}
	WHILE:while (1) {
		$flag = 0;
		my $n = 35; if ($param->{SORT_BY_PEDID}) { $n=1 }
		FOR:for my $n ( 1 .. $n ) {		
						
			BuildMatrix($fam);				
			my $count = 0; until (AlignMatrix($fam)) { $count++ ; last if $count > $param->{MAX_COUNT} }											
			SetLines($fam);
			my $c = CountLineCross($fam);
			unless ($c) {					
				SetSymbols($fam);				
				SetHaplo($fam);
				last WHILE
			}
			
			if (! $batch) {
				my $text = sprintf("%9s%18s%20s  ","Try #$n", "Crosses #$c", "min crosses #$CrossMin");
				$param->{INFO_LABEL}->configure(-text => $text);
				$mw->update();
			}
			
			$CrossMin = $c unless $CrossMin;
		
			if ($c < $CrossMin) {
				$CrossMin = $c;
				$save = freeze($self);
				$flag = 1;
				last FOR;
			}
			else {			
				FindTop($fam);
				BuildStruk($fam);							
			}
		}
		
		unless ($flag) {
			$self = thaw($save) if $save;
			SetSymbols($fam);		
			SetHaplo($fam);
			last WHILE;
		}
	}
	if (!$batch) {
		$self->{GLOB}{CURSOR} = $cursor;
		$canvas->configure(-cursor => $self->{GLOB}{CURSOR});
		$canvas->update();
	}
	
	1;
}

# $self will be stored by Storable ...
#=============
sub SaveSelf {
#=============	
	return unless $self->{GLOB}{CURR_FAM};
	if ($_[0] || !$self->{GLOB}{FILENAME_SAVE}) {
		$_ = $mw->getSaveFile(
			-initialfile 	=> basename($self->{GLOB}{FILENAME}),
			-defaultextension	=> 'hp', -filetypes		=> [ [ 'All Files',	 '*' ], [ 'HaploPainter Files', 'hp' ] ]
		) or return undef;
		$self->{GLOB}{FILENAME} = $_;
		$self->{GLOB}{FILENAME_SAVE} = 1;
	} else {
		$_ = $self->{GLOB}{FILENAME} or return undef
	}
	$canvas->configure(-cursor => 'watch');
	store $self, $_;
	$canvas->configure(-cursor => $self->{GLOB}{CURSOR});
}

#====================
sub RestoreSelfGUI {
#====================
	my $file = $mw->getOpenFile() or return undef;
	RestoreSelf($file,1);
	$self->{GLOB}{FILENAME} = $file;
	$self->{GLOB}{FILENAME_SAVE} = 1;
}

# ... and restored ...
#================
sub RestoreSelf {
#================	
	my ($file, $flag) = @_ or return undef;
	my $test; eval { $test = retrieve($file) };
	if ($@ && $flag) { ShowInfo "File reading error!\n$@", 'warning'; return undef}
	if ($@ && ! $flag) { return undef }
	
	### check for compatability --> old Versions do not have this variable
	### if changes in save format break backward compatibility --> do it here
	if ( ! $test->{GLOB}{VERSION} ) {
		ShowInfo "This version of HaploPainter does not support the specified file format!", 'warning'; return 
	}
	
	$self =$test;
	$canvas->update();
	$canvas->configure(-background  => $self->{GLOB}{BACKGROUND});

	my $fileref = $menubar->entrycget('View', -menu);
	my $drawref = $fileref->entrycget('Draw Pedigree ...', -menu);
	$drawref->delete(0,'end');
	
	for my $fam (nsort keys % { $self->{FAM}{PED_ORG} }) { 
		$drawref->add('command', -label => $fam, -command => sub {DrawOrRedraw($fam)} ) 
	}
	
	RedrawPed();
	AdjustView(-fit => 'center');
	1;
}

###  Loops there? If yes store information for later queries
#==============
sub FindLoops {
#==============	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $s = $self->{FAM}{LOOP}{$fam} = {};
	my (%path, $flag, %P, %N, %D, %D1, %D2, %K, %L, %B);
	my $node_cc = 1;
	
	### network for loop detection
	### couples as nodes
	foreach my $node ( keys % { $self->{FAM}{PARENT_NODE}{$fam} }) {
		my ($fid, $mid) = @ { $self->{FAM}{PARENT_NODE}{$fam}{$node} };
		
		### check for parent nodes
		foreach my $parent ($fid, $mid) {
			if ( defined $self->{FAM}{SID2FATHER}{$fam}{$parent} && defined $self->{FAM}{SID2MOTHER}{$fam}{$parent} ) {
				my ($fpar, $mpar) = ($self->{FAM}{SID2FATHER}{$fam}{$parent}, $self->{FAM}{SID2MOTHER}{$fam}{$parent});
				my $parnode = join '==', nsort($fpar, $mpar);
				$N{$node}{$parnode} = 1;
			}
		}
		
		### check for child nodes
		foreach my $child ( keys % { $self->{FAM}{CHILDREN_COUPLE}{$fam}{$fid}{$mid} }) {
			if (defined $self->{FAM}{CHILDREN_COUPLE}{$fam}{$child}) {
				foreach my $mate (keys % { $self->{FAM}{CHILDREN_COUPLE}{$fam}{$child} }) {
					my $parnode = join '==', nsort($child, $mate);
					$N{$node}{$parnode} = 1;
				}
			}	
		}
		
		### create joining parent node for multiple mates without shared parents
		foreach my $parent ( keys % { $self->{FAM}{CHILDREN_COUPLE}{$fam} } ) {			
			### is this a multiple mate situation?
			if (scalar (keys % { $self->{FAM}{CHILDREN_COUPLE}{$fam}{$parent} }) > 1) {				
				### there is no parent node for this set of multiple mate child nodes
				if (! defined $self->{FAM}{SID2FATHER}{$fam}{$parent} && ! defined $self->{FAM}{SID2MOTHER}{$fam}{$parent} ) {					
					### pseudo node creation to connect joined mates by one parent node
					my @mates = nsort keys % { $self->{FAM}{CHILDREN_COUPLE}{$fam}{$parent} };
					my $node = 'PSNODE_' . join ('==', (@mates, $parent)) . '_PSNODE';
					
					foreach my $mate (@mates) {
						my $parnode = join '==', nsort($parent, $mate);
						$N{$node}{$parnode} = 1;
						$N{$parnode}{$node} = 1;
					}
				}
			}
		}
	}
		
	### prepare start tree including root and one further level
	foreach my $node1 (keys %N) {		
		foreach my $node2 (keys % { $N{$node1} }) {
			$path{$node_cc} = [ $node1, $node2 ]; $node_cc++;
		}
	}
	#print Dumper(\%path);
	### This code evaluates all loops, clock/anticlock 
	### at every start position inside the loop
	W:while (!$flag) {
		$flag = 1;
		foreach my $p (keys %path) {
			my $r = $path{$p};
			my @plist = @$r;			
			next if $r->[-1] eq 'LOOP';
			
			### delete this path and substitute it by child pathes next in code
			### If there is no path to subsitute it is removed by the way											
			delete $path{$p};
			
			### spacial case inter sibling mate 
			my ($pid1, $pid2) = split '==', $r->[-1];					
			### both sibling and halfsibling mates (may be better handle as separate cases)
			if (defined $self->{FAM}{SID2FATHER}{$fam}{$pid1} && defined $self->{FAM}{SID2FATHER}{$fam}{$pid2} &&
				defined $self->{FAM}{SID2MOTHER}{$fam}{$pid1} && defined $self->{FAM}{SID2MOTHER}{$fam}{$pid2}) {
				if (($self->{FAM}{SID2FATHER}{$fam}{$pid1} eq $self->{FAM}{SID2FATHER}{$fam}{$pid2}) or 
					($self->{FAM}{SID2MOTHER}{$fam}{$pid1} eq $self->{FAM}{SID2MOTHER}{$fam}{$pid2})) {
					#$path{$node_cc} = [ @plist, 'LOOP' ];  $node_cc++; next W	
					$s->{CONSANGUINE}{$pid1}{$pid2} = 1;
					$s->{CONSANGUINE}{$pid2}{$pid1} = 1;
					$_ = join '==', nsort($pid1,$pid2);
					$s->{CONSANGUINE_ORG}{$_} = 1;					
				}
			}
			
			### there is only one way back --> delete this path
			my @subnodes = keys % { $N{ $r->[-1] } };
			next if scalar @subnodes == 1;
			
			### look for subnodes
			F:foreach my $node (@subnodes) {
				### dont go back inside the path!
				next if $node eq $plist[-2];
				### unperfect LOOP --> no further processing
				for ( 1 .. scalar @plist-1 ) { next F if $plist[$_] eq $node }
				### perfect LOOP ( start = end)
				if ($node eq $plist[0]) { $path{$node_cc} = [ @plist, 'LOOP' ];  $node_cc++  }		
				### expand paths by subnodes else				
				else { 										
					$path{$node_cc} = [ @plist, $node ]; $node_cc++; undef $flag 
				}
			}
		}		
	}	
	
	### processing paths to find duplicates
	foreach my $node (keys %path) {		
		@_ = ();
		foreach (@ {$path{$node}}) {
			### remove LOOP-end tag and pseudonodes
			next if /LOOP|PSNODE/;
			push @_, $_;
		}
		$_ = join '___', nsort(@_);
		$D{$_} = [ @_ ];
		foreach my $e (@_) { $D1{$_}{$e} = 1 }
	}
	
	### return if no loops there
	return unless keys %D;
	
	## if a small loop is part of a bigger loop store this information	
	foreach my $loop1 (keys %D1) {
		foreach my $loop2 (keys %D1) {
			next if $loop1 eq $loop2;
			my ($lp1, $lp2);
			if (  (scalar keys % { $D1{$loop1} }) <  (scalar keys % { $D1{$loop2} }) ) {
				($lp1, $lp2) = ($loop1, $loop2);
			}
			elsif (  (scalar keys % { $D1{$loop1} }) >  (scalar keys % { $D1{$loop2} }) ) {
				($lp1, $lp2) = ($loop2, $loop1);
			}			
			if ($lp1) {
				my $flag;
				foreach my $k (keys % { $D1{$lp1} }) { $flag = 1 if ! $D1{$lp2}{$k} }													
				$D2{$lp2} = 1 if ! $flag								
			}
		}
	}
	
	### analyse loop structure
	### find start, middle and end nodes/individuals
	### start nodes/individuals have no parent node but children nodes
	### middle nodes have start and end nodes
	### end nodes have no children but parent nodes	
	my $countl = 0;	
	foreach my $loop (keys %D) {
		my %start_nodes;
		$countl++;
		my @loop_list = @ {$D{$loop}};
		#print Dumper(\@loop_list);
		my %E;
		### build Hash for every individual inside the loop 
		foreach my $couple (@loop_list) {
			foreach my $pid (split '==', $couple) {
				$E{$pid} = 1;
			}
		}
		
		### exploring loop
		my @node_types;
		foreach my $node (@loop_list) {
			my ($p1, $p2) = (split '==', $node);
			
			### there is a chance that this is a multiple mate case and
			### one of that mate is further connected
			
			### getting all connected mates of this node which are part of the loop
			my %P = ( $p1, 1, $p2, 1);			
			W:while (1) {
				undef $flag;
				foreach my $p ( keys %P ) {
					foreach my $c ( keys % { $self->{FAM}{COUPLE}{$fam}{$p} }) {
						if (! $P{$c} && $E{$c}) { $P{$c} = 1; $flag = 1 }
					}
				}
				last W unless $flag
			}
			
			my ($no_start_flag, $no_end_flag) = (0,0);
			foreach my $p (keys %P) {
				### this cannot be a start node
				if ($self->{FAM}{SID2FATHER}{$fam}{$p} && $E{$self->{FAM}{SID2FATHER}{$fam}{$p}})  { $no_start_flag = 1 }
				if ($self->{FAM}{SID2MOTHER}{$fam}{$p} && $E{$self->{FAM}{SID2MOTHER}{$fam}{$p}})  { $no_start_flag = 1 }
				
				### this cannot be a end node
				foreach my $p1 (keys %P) {
					foreach my $p2 (keys %P) {
						if ($self->{FAM}{CHILDREN_COUPLE}{$fam}{$p1}{$p2}) {
							foreach my $child (keys %{$self->{FAM}{CHILDREN_COUPLE}{$fam}{$p1}{$p2}}) {
								if ($E{$child}) { $no_end_flag = 1 }
							}
						}
					}
				}
			}
						
			### START nodes
			if (! $no_start_flag && $no_end_flag) {
				$s->{START}{$p1}{$p2} = 1;
				$s->{START}{$p2}{$p1} = 1;
				$s->{NR2START}{$countl}{$p1} = 1;
				$s->{NR2START}{$countl}{$p2} = 1;
				if ( (scalar keys %P) > 2 ) { 
					push @node_types, 'SM';
				}
				else { push @node_types, 'S_' }
			}
			
			### END nodes
			elsif ( $no_start_flag && ! $no_end_flag) {
				$s->{END}{$p1}{$p2} = 1;
				$s->{END}{$p2}{$p1} = 1;				
				$s->{NR2END}{$countl}{$p1} = 1;
				$s->{NR2END}{$countl}{$p2} = 1;
				
				if ( (scalar keys %P) > 2 ) { 
					push @node_types, 'EM';
				}
				else {
					if ($self->{FAM}{COUPLE}{$fam}{$p1} && $self->{FAM}{COUPLE}{$fam}{$p1}{$p2}) {
						$s->{CONSANGUINE}{$p1}{$p2} = 1;
						$s->{CONSANGUINE}{$p2}{$p1} = 1;
						$_ = join '==', nsort($p1,$p2);
						$s->{CONSANGUINE_ORG}{$_} = 1;
					}
					push @node_types, 'E_' 
				}			
			}
			
			### MIDDLE nodes
			elsif ( $no_start_flag && $no_end_flag) {
				$s->{MIDDLE}{$p1}{$p2} = 1;
				$s->{MIDDLE}{$p2}{$p1} = 1;				
				$s->{NR2MIDDLE}{$countl}{$p1} = 1;
				$s->{NR2MIDDLE}{$countl}{$p2} = 1;
				if ( (scalar keys %P) > 2 ) { 
					push @node_types, 'MM';
				}
				else { push @node_types, 'M_' }	
			}
		}
				
		### this is a hard to draw loop (found no end nodes in it)  --> mark proper nodes as consanguine
		if (! defined $s->{NR2END}{$countl}) {
			my %R;
			foreach my $node (@loop_list) {
				foreach my $p (split '==', $node) {
					if ($R{$p}) {
						foreach my $mate (keys % { $self->{FAM}{COUPLE}{$fam}{$p} }) {
							if ($E{$mate}) {							
								if ($self->{FAM}{SID2MOTHER}{$fam}{$mate} && $E{$self->{FAM}{SID2MOTHER}{$fam}{$mate}} && $self->{FAM}{SID2FATHER}{$fam}{$mate} && $E{$self->{FAM}{SID2FATHER}{$fam}{$mate}}) {										
									if ($self->{FAM}{COUPLE}{$fam}{$p} && $self->{FAM}{COUPLE}{$fam}{$p}{$mate}) {									
										$s->{CONSANGUINE}{$p}{$mate} = 1;
										$s->{CONSANGUINE}{$mate}{$p} = 1;
										$_ = join '==', nsort($p,$mate);
										$s->{CONSANGUINE_ORG}{$_} = 1;
									}	
								}
							}
						}
					}
					$R{$p}++;
				}				
			}
			
			### store those nodes including individuals occuring more then one time in all nodes from the loop
			### such individuals are candidates for breaking a loop
			foreach my $p1 (keys %R) {
				if ($R{$p1}>1) {
					foreach my $node (@loop_list) {
						foreach my $p2 (split '==', $node) {
							if ($p1 eq $p2) {
								$B{PID}{$p1}{$node} = 1;		
							}
						}
					}
				}
			}
		}

		### detection of "asymetric" loops
		### When loops are not in balance - that means that there are more middle nodes on the one side
		### then the other, the end note person which belongs to the side with lower middle notes 
		### must be prevented to draw in the middle part.		
		### It also has to be explored, if middle nodes belong to a multiple mate group (they count as one node together)				
		
		### loop twice over loop_list 
		### exploring number of middle nodes from START --> END
		my $cll = scalar @loop_list;
		my $cc1 = 0;
		my $i1;
		undef $flag;
		for my $i ( -$cll .. $cll-1 ) {
			if ($node_types[$i] =~ /S./) { $flag = 1; next }
			next unless $flag;      
			
			if ($node_types[$i] =~ /E./) {
				$i1 = $i;
				last
			}
			if ( (($node_types[$i] =~ /MM/) && ($node_types[$i-1] !~ /MM/)) or  ($node_types[$i] =~ /M_/)) {
				$cc1++; 
			}
		}
		
		### loop twice over loop_list 
		### exploring number of middle nodes from END --> START
		my $cc2 = 0;
		my $i2;
		undef $flag;
		for my $i ( -$cll .. $cll-1 ) {
			if ($node_types[$i] =~ /E./) { $flag = 1; next }
			next unless $flag;      
			if ($node_types[$i] =~ /S./) {
				$i2 = $i;
				last
			}	

			if ( (($node_types[$i] =~ /MM/) && ($node_types[$i-1] !~ /MM/)) or  ($node_types[$i] =~ /M_/)) {
				$cc2++;
			}
		}
		
		##### asymetric loop !!!
		if ( ($cc1 != $cc2) &&  ! $D2{$loop} ) {
			my ($n1, $n2);
			for my $i ( 1-$cll .. $cll-1 ) {			
				if ( 	($cc1 < $cc2) && ($node_types[$i] =~ /E./) && ($node_types[$i-1] =~ /M.|S./) ) {
					($n1, $n2) = @loop_list[$i-1, $i];
				}
				elsif ( ($cc1 > $cc2) && ($node_types[$i] =~ /M.|S./) && ($node_types[$i-1] =~ /E./) ) {
					($n1, $n2) = @loop_list[$i, $i-1];
				}
				
			}
			
			# very hard loop -> take a try		
			if (! $n1) {
				if ($node_types[0] =~ /S./) { ($n1, $n2) = @loop_list[0, -1] }
				else { ($n1, $n2) = @loop_list[-1, 0] }
			}
						
			my ($p1, $p2) = split '==', $n1;
			my ($p3, $p4) = split '==', $n2;
						
			if ( defined $self->{FAM}{CHILDREN_COUPLE}{$fam}{$p1}{$p2}{$p3} ) {
					$s->{DROP_CHILDREN_FROM}{$p3} = 1
			} 
			if ( defined $self->{FAM}{CHILDREN_COUPLE}{$fam}{$p1}{$p2}{$p4} ) {
				$s->{DROP_CHILDREN_FROM}{$p4} = 1
			}
		}
	}
	
	### some nodes could be common part of multiple loops
	### such nodes should be get off from individual duplication to prevent trouble
	foreach my $p ( keys % { $B{PID} } ) {
		foreach my $node ( keys % { $B{PID}{$p} } ) {
			$B{NODE}{$node}++;		
		}
	}

	#### mark indviduals for loop breaking in case of hard core loops
	if (keys %B) {
		foreach my $p ( keys % { $B{PID} } ) {
			my (@nodes, $flag);
			foreach my $node (keys % { $B{PID}{$p} }) {
				if ($B{NODE}{$node} == 1) { push @nodes, $node }
				else {$flag = 1}
			}
			ChangeOrder(\@nodes);
			shift @nodes if ! $flag;
			
			foreach (@nodes) {	
				my ($p1, $p2) = split '==', $_;
				if ($p eq $p1) {$s->{BREAK}{$p}{$p2} = 1} 
				else { $s->{BREAK}{$p}{$p1} = 1 }
			}						
		}
	}
	
	$s->{LOOP_COUNT} = $countl;
		
	### skip loops that end on same node
	### make new data structur for this task
	my %dupl;
	foreach my $loop (keys % { $s->{NR2END} }) {
		@_ = nsort keys % { $s->{NR2END}{$loop} };
		$_ = join '==', @_;
		$dupl{$_} = [ $loop , @_ ];		
	}	
	foreach my $k (keys %dupl) {
		my $nr = shift @ { $dupl{$k} };
		foreach ( @ { $dupl{$k} }) {
			$s->{NR2END_UNIQUE}{$nr}{$_} = 1
		}
	}
		
	### find loops that are not part of other loops
	my %skip;
	foreach my $loop1 (keys % { $s->{NR2END_UNIQUE} }) {
		my $c1 = scalar keys % { $s->{NR2END_UNIQUE}{$loop1} };
		foreach my $loop2 (keys % { $s->{NR2END_UNIQUE} }) {
			next if $loop1 == $loop2;
			my $c2 = scalar keys % { $s->{NR2END_UNIQUE}{$loop2} };
			if ($c1 > $c2) {
				my $cc = 0;
				foreach my $p ( keys % { $s->{NR2END_UNIQUE}{$loop2} }) {
					$cc++ if $s->{NR2END_UNIQUE}{$loop1}{$p}
				}
				### make skip list	
				$skip{$loop1} = 1 if $cc == $c2;
			}
		}
	}
	
	
	### preformat the BREAK_LOOP_OK structure if LOOP_BREAK_STATUS is not 3 (manually selected loop breaks)
	foreach my $loop (keys % { $s->{NR2END_UNIQUE} }) {
		next if $skip{$loop};
		my @p = nsort keys % { $s->{NR2END_UNIQUE}{$loop} };
		$_ = join '==', @p;							
		if ($self->{FAM}{LOOP_BREAK_STATUS}{$fam} == 2) {			
			$self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} = 1;
		}
		elsif ($self->{FAM}{LOOP_BREAK_STATUS}{$fam} == 0) {
			$self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} = 0
		}
	}
}


# Read and process haplotype information from different sources
#==============
sub ReadHaplo {
#==============	
	my (%arg) = @_;
	open (FH, "<" , $arg{-file}) or (ShowInfo("$!: $arg{-file}", 'warning'), return );
		my @file = (<FH>);
	close FH;

	unless (@file) { ShowInfo("$arg{-file} has no data !", 'warning'); return undef }
	my $h1;
	my %haplo;
	my %map;
	my %merlin_unknown = ( qw / ? 1 . 1 / );
	
	### read multiple times searching for given family
	### sample IDs are substituted during processing
	### only haplotypes from those individuals inside pedigree files are imported
	### and only if the sample name matches exact
	foreach my $fam (nsort keys % { $self->{FAM}{PED_ORG} }) {	
		my $found_fam = 0;
		
		### SIMWALK -> one family - one file		
		if ($arg{-format} eq 'SIMWALK') {
			for (my $i = 0; $i < $#file,; $i++) {
				$_ = $file[$i];
				if (/The results for the pedigree named: $fam/) {
					$found_fam = 1;
					undef $haplo{$fam};
					$h1 = $haplo{$fam}{PID} = {};
				}
				next unless $found_fam;
				if (/^M /) {
					my ($M, $z, $P) = ($_,$file[++$i], $file[++$i] );
					my ($pid, $haplo);
					if ( ($pid, $haplo) = $M =~ /^M (\S+).+\s{7}([0-9@].+[0-9@])\s+$/) {
						$pid = $self->{FAM}{PID2PIDNEW}{$fam}{$pid} or next;
						$h1->{"$pid"}{M}{TEXT} = [ split ' ', $haplo ];
						s/\@/$self->{FAM}{HAPLO_UNKNOWN}{$fam}/ foreach @{$h1->{"$pid"}{M}{TEXT}};
					} else {
						ShowInfo("Having problems in finding maternal haplotype in line\n$M", 'error'); return undef
					}
					if ( ($pid, $haplo) = $P =~ /^P (\S+).+\s{7}([0-9@].+[0-9@])\s+$/) {
						$pid = $self->{FAM}{PID2PIDNEW}{$fam}{$pid} or next;
						$h1->{"$pid"}{P}{TEXT} = [ split ' ', $haplo ];
						s/\@/$self->{FAM}{HAPLO_UNKNOWN}{$fam}/ foreach @{$h1->{"$pid"}{P}{TEXT}};
					} else {
						ShowInfo("Having problems in finding paternal haplotype in line\n$P", 'error'); return undef
					}
				}
			}
		}

		### GENEHUNTER 
		elsif ($arg{-format} eq 'GENEHUNTER') {			
			my $fam;
			for (my $i = 0; $i < $#file,; $i++) {
				$_ = $file[$i];
				chomp;
				next unless $_;
				if (/^\*+\s+(\S+)\s+/) {
					next unless $self->{FAM}{PED_ORG}{$1};
					$fam = $1 ;
					$h1 = $haplo{$fam}{PID} = {};
					next;
				}
				next unless $fam;
				my ($P, $M) = ($_,$file[++$i]);
				my ($pid, undef, undef, undef, $PH)  = split "\t", $P;				
				$pid = $self->{FAM}{PID2PIDNEW}{$fam}{$pid} or next;
				$h1->{$pid}{P}{TEXT} = [ split ' ', $PH ];
				foreach (@{$h1->{$pid}{P}{TEXT}}) { s/0/$self->{FAM}{HAPLO_UNKNOWN}{$fam}/ if $_ eq '0' }
				$M =~ s/\t//g;
				$h1->{$pid}{M}{TEXT} = [ split ' ', $M ];
				foreach (@{$h1->{$pid}{M}{TEXT}}) { s/0/$self->{FAM}{HAPLO_UNKNOWN}{$fam}/ if $_ eq '0' }
			}
		}

		### MERLIN 
		elsif ($arg{-format} eq 'MERLIN') {
			my ($fam, @p);
			
			foreach (@file) {				
				chomp;	
				next unless $_;
				
				### extracting family ID
				if (/^FAMILY\s+(\S+)\s+\[(.+)\]/) {
					undef $fam; undef @p;
					next if $2 eq 'Uninformative';													
					next unless $self->{FAM}{PED_ORG}{$1};
					$fam = $1;					
					$h1 = $haplo{$fam}{PID} = {};
				}				 
				next unless $fam;	
				
				### extracting individual IDs
				if (/\(.+\)/) {					
					@p = ();
					my @pid = split ' ', $_;					
					for ( my $k = 0; $k < $#pid; $k+=2 ) {
						
						my $pid = $self->{FAM}{PID2PIDNEW}{$fam}{$pid[$k]} or next;
						push @p,$pid;
						$h1->{$pid}{M}{TEXT} = [];
						$h1->{$pid}{P}{TEXT} = [];
					}
					next									
				}				
				next unless @p;				
				
				### extracting genotype data
				my @L = split;
				next unless @L; 				  				
				for (my $m = 0; $m <= $#p; $m++ ) {
					my $pid = $p[$m];
					my $z = $L[$m*3]; if ($z =~ /,/) { @_ = split ',',$z; $z = $_[0] };
					$z =~ s/[A-Za-z]//g;
					$z = $self->{FAM}{HAPLO_UNKNOWN}{$fam} if $merlin_unknown{$z};
					push @{$h1->{$pid}{M}{TEXT}}, $z;
					my $g = $L[($m*3)+2]; if ($g =~ /,/) { @_ = split ',',$g; $g = $_[0] };
					$g =~ s/[A-Za-z]//g;
					$g = $self->{FAM}{HAPLO_UNKNOWN}{$fam} if $merlin_unknown{$g};
					push @{$h1->{$pid}{P}{TEXT}}, $g;
				}																
			}						
		}
				
		### ALLEGRO 
		elsif ($arg{-format} eq 'ALLEGRO') {
			foreach (@file) { @_ = split; undef $haplo{$_[0]} if $_[0] }
			for (my $i = 0; $i < $#file; $i++) {
				$_ = $file[$i];
				chomp;
				next unless $_;
				next if /^       /;
				@_ = split; 
				next unless @_;
				next unless $self->{FAM}{PED_ORG}{$_[0]};
				my $fam = $_[0];
				my $p = $self->{FAM}{PID2PIDNEW}{$fam}{$_[1]} or next;
				$haplo{$fam}{PID}{$p}{P}{TEXT} = [ @_[ 6 .. $#_] ];
				@_ = split ' ', $file[++$i]; 
				next unless @_;
				next unless $self->{FAM}{PED_ORG}{$fam};
				$haplo{$fam}{PID}{$p}{M}{TEXT} = [ @_[ 6 .. $#_] ];
			}
		}
	
		else { ShowInfo ("Unknown haplotype file format $arg{-format} !", 'info') ; return undef }   
	}
	
	return unless %haplo;
	
	### produce 'dummy map' when haplotype information are loaded
	### this is replaced later when 'real' map files come in
	foreach my $fam ( keys %haplo ) {
		$self->{FAM}{HAPLO}{$fam} = $haplo{$fam};
		(my $pid) = keys %{ $self->{FAM}{HAPLO}{$fam}{PID} } or next;
		if ( $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{TEXT} ) {
			for my $i ( 0 .. $#{ $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{TEXT} } ) {
				$self->{FAM}{HAPLO}{$fam}{DRAW}[$i] = 1;
				$map{MARKER}[$i] = 'Marker' . sprintf("%02.0f",$i+1) unless $map{MARKER}[$i];
			}
			$self->{FAM}{MAP}{$fam} = \%map;				
		}			
	}
	
	ShuffleFounderColors();
	ProcessHaplotypes();
	RedrawPed();	
	AdjustView() if !$batch;	
	
	1;
}

### Loop breaking adds new individuals. 
### Haplotypes have to be duplicated thus
#========================
sub DuplicateHaplotypes {
#========================
	###in case of duplicated PIDs copy the haplotype information
	foreach my $fam ( keys % { $self->{FAM}{HAPLO} } ) {
		foreach my $pid ( keys %{ $self->{FAM}{HAPLO}{$fam}{PID} } ) {	
			if ($self->{FAM}{DUPLICATED_PID}{$fam}{$pid}) { 
				foreach my $pid_n (keys % { $self->{FAM}{DUPLICATED_PID}{$fam}{$pid} }) {
					$self->{FAM}{HAPLO}{$fam}{PID}{$pid_n}{P}{TEXT}  = [ @ { $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{TEXT} } ];
					$self->{FAM}{HAPLO}{$fam}{PID}{$pid_n}{M}{TEXT}  = [ @ { $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{TEXT} } ];
				}
			}
		}
	}
	1;
}


# Read map files 
#============
sub ReadMap {
#============	
	my (%arg) = @_;
	if ($arg{-file}) {
		open (FHM, "<" , $arg{-file}) or ShowInfo("$! $arg{-file}",'warning') && return;
			while (<FHM>) { ${$arg{-data}} .= $_ } 
		close FHM;
	}
	unless ($arg{-data}) { ShowInfo("No data to read !", 'warning'); return undef }
	
	### for which families the map sould be imported
	### the global flag GLOBAL_MAP_IMPORT leads to import of mapping data for every family
	my @fam = ($self->{GLOB}{CURR_FAM});
	if ($param->{GLOBAL_MAP_IMPORT}) { @fam = keys %{ $self->{FAM}{PED_ORG} } }	
	my %map = ();
	
	### CHR-POS-MARKER Format
	if ($arg{-format} eq '1') {
		my $i = 0; foreach (split "\n", ${$arg{-data}}) {
			next unless $_;
			s/\t/ /g;
			next if /^[#!*\/]|CHR/i;
			my ($chr, $pos, $marker) =  split ' ', $_;
			next if ( ! $chr || ! defined $pos || ! $marker );
			$map{POS}[$i] = $pos;
			$map{MARKER}[$i] = $marker;
			$i++;
		}
	}
	
	### CHR-MARKER-POS
	elsif ($arg{-format} eq '2') {
		my $i = 0; foreach (split "\n", ${$arg{-data}}) {
			next unless $_;
			s/\t/ /g;
			next if /^[#!*\/]|CHR/i;
			my ($chr, $marker, $pos) =  split ' ', $_;
			next if ( ! $chr || ! defined $pos || ! $marker );
			$map{POS}[$i] = $pos;
			$map{MARKER}[$i] = $marker;
			$i++;
		}
	}
	
	### catch wrong positions, converting of , --> . 
	foreach ( @ { $map{POS} } ) {
		s/,/\./g;
		if (/[^-+.0-9]/) {
			ShowInfo("One ore more marker positions are corrupted!\n$_",'warning');
			return undef;
		}
	}
	
	### import map for every family	
	my $sm = scalar @{$map{MARKER}};	
	foreach my $fam (@fam) {		
		my $sc; 
		if ( $self->{FAM}{MAP}{$fam}{MARKER} &&  @{$self->{FAM}{MAP}{$fam}{MARKER}}) { 
			$sc = scalar @{$self->{FAM}{MAP}{$fam}{MARKER}} 
		}		
		if ( $sc && ($sc != $sm) ) {
			
			if ($param->{GLOBAL_MAP_IMPORT}) {
				if (scalar @fam ==1) {
					ShowInfo("This map file consists of more or less marker ($sm) then have been loaded from the haplotype file ($sc) for family $fam!",'warning');
					return undef;
				}
				else {
					ShowInfo("This map file consists of more or less marker ($sm) then have been loaded from the haplotype file ($sc) for family $fam!\n" .
					"You should switch off the 'Global map import' flag if your map file is not valid for every family.",'warning'); next
				}
			}
			else {
				ShowInfo("This map file consists of more or less marker ($sm) then have been loaded from the haplotype file ($sc) for family $fam!",'warning');
				return undef;
			}
		}
		undef $self->{FAM}{MAP}{$fam}{POS};
		undef $self->{FAM}{MAP}{$fam}{MARKER};
		foreach my $pos (@ {$map{POS}}) { push @ { $self->{FAM}{MAP}{$fam}{POS} }, $pos }
		foreach my $marker (@ {$map{MARKER}}) { push @ { $self->{FAM}{MAP}{$fam}{MARKER} }, $marker }
	}
	1;
}


# Reading pedigree information
#============
sub ReadPed {
#============	
	my (%arg) = @_;
	return unless $arg{-file};
	
	undef $self->{GLOB}{IMPORTED_PED};
	my $encoding = '';
	
	### read in first 4 bytes to check for BOM sequence
	my ($bom, $file, $bflag);
	open (IN, "<" , $arg{-file}) or (ShowInfo("$! $arg{-file}",'warning'), return undef);
	binmode IN;
	read(IN, $bom,4);			
	close IN;
	
	### file is emty or truncated
	return unless $bom;
	my %e = (
		ascii => '<',utf8 => '<:utf8', 
		utf16be => '<:encoding(UTF-16BE)',utf16le => '<:encoding(UTF-16LE)',
		utf32be => '<:encoding(UTF-32BE)',utf32le => '<:encoding(UTF-32LE)'
	);		
	
	### HaploPainter deals with BOM/Unicode sequence in a way that it checks for it
	### and if there it will overides the $param->{ENCODING} flag
	if    ($bom =~ /^\xEF\xBB\xBF/) 		{ $bflag=1; $encoding = $e{utf8} }
	elsif ($bom =~ /^\x00\x00\xFE\xFF/) { $bflag=1; $encoding = $e{utf32be}  }
	elsif ($bom =~ /^\xFF\xFE\x00\x00/) { $bflag=1; $encoding = $e{utf32le}  }
	elsif ($bom =~ /^\xFE\xFF/) 				{ $bflag=1; $encoding = $e{utf16be}  }
	elsif ($bom =~ /^\xFF\xFE/) 				{ $bflag=1; $encoding = $e{utf16le}  }
	elsif ($param->{ENCODING}) 		{ $encoding = $e{$param->{ENCODING}} }

	open (FH, $encoding , $arg{-file}) or (ShowInfo("$! $arg{-file}",'warning'), return undef);
		### removing BOM if there
		if ($bflag) {
			if (defined ($_ = <FH>)) {
				s/^\x{FEFF}//; 
				$file .= $_ 
			}
			else {
				ShowInfo("Read error",'warning');
				return undef;
			}
		}
	
		
		while (defined ($_ = <FH>)) {
			$file .= $_
		}
		
		
	close FH;
 
	ShowInfo("File $arg{-file} is emty !", 'warning') unless $file;

	#########################################################################
	### Step 1 : read PedData in ARRAY
	#########################################################################

	my %ped_org;
	my %t = (qw/n 0 N 0 y 1 Y 1 0 0 1 1/);
	
	### LINKAGE format --- delimiter = 'tab' or ';' or 'space' --> must have 6 fields
	### HaploPainter trys to process lines in a way that delimiters are automatically dedected
	
	### Syntax of LINKAGE format
	###
	###	           FAMILY                   [ text ]
	###	           PERSON                   [ text ]
	###	           FATHER                   [ text ]
	###	           MOTHER                   [ text ]
	###	           GENDER                   [ [0 or x], [1 or m] ,[2 or f] ]
	###	           AFFECTION                [ [0 or x], 1,2,3,4,5,6,7,8,9 ]
	
	if ( uc $arg{-format} eq 'LINKAGE' ) {
		foreach my $l (split "\n", $file) {
			next unless $l;
			### signs '#' or '*' or '!' may be used to integrate comments or header rows into the file
			next if $l =~ /^[#!*\/]/;
			$l =~ s/^\s+//; $l =~ s/\s+$//;
			$l =~ s/^;+//; $l =~ s/;+$//;
			
			if ($l =~ /;/) { 
				@_ = split ";" ,$l;
				if (scalar @_ < 6) {$l =~ s/;+//g; @_ = split ' ', $l}	### signs '#' or '*' or '!' may be used to integrate comments or header rows into the file						
			}
			
			elsif ($l =~ /\t/) { 
				@_ = split "\t+" ,$l;				
				if (scalar @_ < 6) {@_ = split ' ', $l}				
			}
			
			else { @_ = split ' ' ,$l }						
			next unless @_;
			next if scalar @_ < 6;
			foreach (@_) { s/^\s+//; s/\s+$// }							
			my $fam = shift @_;
			$fam = '' unless $fam;	
			push @{ $ped_org{$fam} }, [ @_[0..4] ];
		}
	}

	### CSV format --- delimiter = TAB; number of fields are unlimited
	### columns 1 - 6 have same order as LINKAGE format

	###	 0          FAMILY                   [ text ]
	###	 1          PERSON                   [ text ]
	###	 2          FATHER                   [ text ]
	###	 3          MOTHER                   [ text ]
	###	 4          GENDER                   [ [0 or x], [1 or m] ,[2 or f] ]
	###	 5          AFFECTION                [ [0 or x], 1,2,3,4,5,6,7,8,9 ]
	###	 6     0    IS_DECEASED              [ [NULL or 0 or n], [ 1 or y ] ]
	###	 7     1    IS_SAB_OR_TOP            [ [NULL or 0 or n], [ 1 or y ] ]
	###	 8     2    IS_PROBAND               [ [NULL or 0 or n], [ 1 or y ] ]
	###	 9     3    IS_ADOPTED               [ [NULL or 0 or n], [ 1 or y ] ]
	###	10     4    ARE_TWINS                [ NULL, [m or d]_text ]
	###	11     5    ARE_CONSANGUINEOUS       [ NULL, text ]
	###	12     6    TEXT_INSIDE_SYMBOL       [ NULL, char ]
	### 13     7    TEXT_BESIDE_SYMBOL       [ NULL, text ]
	###	14     8    TEXT1_BELOW_SYMBOL       [ NULL, text ]
	###	15     9    TEXT2_BELOW_SYMBOL       [ NULL, text ]
	###	16    10    TEXT3_BELOW_SYMBOL       [ NULL, text ]
	###	17    11    TEXT4_BELOW_SYMBOL       [ NULL, text ]
	###	18    12    TEXT5_BELOW_SYMBOL       [ NULL, text ]
	
	elsif ( uc $arg{-format} eq 'CSV') {
		foreach my $l (split "\n", $file) {
			next unless $l;
			
			### signs '#' or '*' or '!' may be used to integrate comments or header rows into the file
			next if $l =~ /^[#!*\/]/;
			@_ =  split "\t", $l;
			next unless @_;
			if (scalar @_ < 6) {
				@_ = split ' ', $l;
				next if scalar @_ < 6;
			}
			foreach (@_) { s/^\s+//; s/\s+$// ; undef $_ if $_ eq ''}									
			for (6 ..9) { $_[$_] = $t{$_[$_]} if defined $_[$_] }			
			my $fam = shift @_;	
			$fam = '' unless $fam;		
			push @{ $ped_org{$fam} }, [ @_[0..17] ];
		}
	}
		
	unless (%ped_org) { ShowInfo("There are no data to read !", 'warning'); return undef }	
	my $er = CheckPedigreesForErrors(\%ped_org, $arg{-format});
	if ($er) { ShowInfo($er); return undef }
	
	
	### make a copy of $self to restore it in case of family processing errors
	$param->{SELF_BACKUP} = freeze($self);
		
	### families are attached to self if there are new or replaced if already there
	foreach my $fam (nsort keys %ped_org) { 
		foreach (keys % { $self->{FAM} }) { delete $self->{FAM}{$_}{$fam} if defined $self->{FAM}{$_}{$fam}}
		AddFamToSelf($fam);
		$self->{FAM}{PED_ORG}{$fam} = $ped_org{$fam};
		ProcessFamily($fam) or return;
		FindLoops($fam);
		$self->{GLOB}{IMPORTED_PED}{$fam} = 1;
		
		if (scalar keys % { $self->{FAM}{BREAK_LOOP_OK}{$fam} } > 3) {
			$self->{FAM}{LOOP_BREAK_STATUS}{$fam} = 2;
			foreach (keys % {$self->{FAM}{BREAK_LOOP_OK}{$fam} })  {
				$self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} = 1
			}			
		}				
	}

	1;
}

#============================
sub CheckPedigreesForErrors {
#============================
	my ($pedref, $format) = @_;
	my (@er,$er);
	
	### define regex match for every column
	my %check = (
		LINKAGE => {
			0 => '.+', 1 => '.+', 2 => '.+', 3 => '.+', 4 => '[012xmfXMF]{1}', 5 => '[0123456789xX]{1}'			
		},
		CSV => {
			6 => '[0nN1yY]{1}', 7 => '[0nN1yY]{1}', 8 => '[0nN1yY]{1}', 9 => '[0nN1yY]{1}', 
		 10 => 'M|m|D|d_\w+', 11 => '\w+', 12 => '.{1,3}', 13 => '.{1,3}', 14 => '.+'						
		}
	);
	
	foreach my $fam ( keys %$pedref ) {
		
		foreach my $l ( @ { $pedref->{$fam} } ) {
			@_ = ($fam, @$l);
			
			### obligatory check of first 6 columns
			### they are the same for LINKAGE and CSV format
			for (0 .. 5) {
				if ( ! defined $_[$_] || $_[$_] !~ /^$check{LINKAGE}{$_}$/) {
					foreach (@_[0..5]) { $_ = '' unless defined $_ }
					push @er, "COLUMN= " . ($_+1) . "; WRONG_TERM= '$_[$_]'; LINE= '@_[0..5]'\n"; 
				}
			}	
			
			### additionally information in CSV format is checked for regex match
			if ($format eq 'CSV') {								
				for (6 .. 13) {
					if ( defined $_[$_] && $_[$_] !~ /^$check{CSV}{$_}$/) {
						foreach (@_[0..5]) { $_ = '' unless defined $_ }
						push @er, "COLUMN= " . ($_+1) . "; WRONG_TERM='$_[$_]'; LINE= '@_[0..5]'\n"; 
					}
				}				
				if (scalar @_ > 14) {
					for (14 .. scalar @_-1) {
						if ( defined $_[$_]  &&  $_[$_] !~ /^$check{CSV}{14}$/) {
							foreach (@_[0..5]) { $_ = '' unless defined $_ }
							push @er, "COLUMN= " . ($_+1) . "; WRONG_TERM='$_[$_]'; LINE= '@_[0..5]'\n"; 
						}
					}
				}				
			}
		}
	}
	
	if (@er && scalar @er < 20) {
		$er .= $_ foreach @er;		
		$er = "There are errors in this pedigree file!\n\n$er";
	}
	elsif (@er && scalar @er > 20) {
		for ( 0 .. 19 ) { $er .= $er[$_] }
		$er = "There are too many errors in this pedigree file - only some of them are shown!\n\n$er";
	}
	
	return $er;
}

#==================
sub ProcessFamily {
#==================	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	unless ($fam) { ShowInfo("Achtung : Argumentfehler in Funktion ProcessFamily ", 'error'); return }
	my (@er, $er, %save, %twins, %consang);
	### translate gender values
	my %tgender = (qw/0 0 1 1 2 2 x 0 X 0 m 1 M 1 f 2 F 2/);
	my $ci = $self->{FAM}{CASE_INFO}{$fam} = {};	
	unless ($self->{FAM}{PED_ORG}{$fam}) { ShowInfo("There is no family $fam!",'error'); return undef }

	my $id_counter = 1;	

	### ids of individuals are internally recoded
	foreach my $l (@{$self->{FAM}{PED_ORG}{$fam}}) {
		next unless $l;
		my ($old_sid, $old_fid, $old_mid, $sex, $aff, @sample_info) = @$l;
		my ($sid, $fid, $mid);
		$sex = $tgender{$sex};
		### SID
		if (! $save{$old_sid} ) {
			$sid = $id_counter; 
			$save{$old_sid} = $id_counter;
			$self->{FAM}{PID2PIDNEW}{$fam}{$old_sid}=$id_counter;
			$ci->{PID}{$sid}{'Case_Info_1'} = $old_sid;
			$ci->{COL_TO_NAME}{1} = 'Case_Info_1' ;
			$ci->{COL_NAMES}{Case_Info_1} = 1;		
			$id_counter++;
		}
		$sid = $save{$old_sid};
		
		### FID
		if ($old_fid && ! $save{$old_fid} ) {
			$fid = $id_counter; 
			$save{$old_fid} = $id_counter;
			$ci->{PID}{$fid}{'Case_Info_1'} = $old_fid;
			$self->{FAM}{PID2PIDNEW}{$fam}{$old_fid}=$id_counter;
			$ci->{COL_TO_NAME}{1} = 'Case_Info_1' ;
			$ci->{COL_NAMES}{Case_Info_1} = 1;	
			$id_counter++;
		}
		$fid = $save{$old_fid} || 0;
		
		### MID
		if ($old_mid && ! $save{$old_mid} ) {
			$mid = $id_counter; 
			$save{$old_mid} = $id_counter;
			$ci->{PID}{$mid}{'Case_Info_1'} = $old_mid;
			$self->{FAM}{PID2PIDNEW}{$fam}{$old_mid}=$id_counter;
			$ci->{COL_TO_NAME}{1} = 'Case_Info_1' ;
			$ci->{COL_NAMES}{Case_Info_1} = 1;	
			$id_counter++;
		}
		$mid = $save{$old_mid} || 0;
		
		if ($fid && $mid) {
			
			### father and mother must be different
			if ($fid eq $mid) { push @er, "Father and mother of individual $old_sid are identical!\n"; next }						
			
			### Vater + Mutter jeder Person
			$self->{FAM}{SID2FATHER}{$fam}{$sid} = $fid;
			$self->{FAM}{SID2MOTHER}{$fam}{$sid} = $mid;

			### Kinder der Personen
			$self->{FAM}{CHILDREN}{$fam}{$fid}{$sid} = 1;
			$self->{FAM}{CHILDREN}{$fam}{$mid}{$sid} = 1;

			### Kinder des Paares
			$self->{FAM}{CHILDREN_COUPLE}{$fam}{$fid}{$mid}{$sid} = 1;
			$self->{FAM}{CHILDREN_COUPLE}{$fam}{$mid}{$fid}{$sid} = 1;

			### Partner der Person
			$self->{FAM}{COUPLE}{$fam}{$fid}{$mid} = 1;
			$self->{FAM}{COUPLE}{$fam}{$mid}{$fid} = 1;
			
			### parent node creation
			$_ = join '==', nsort($fid,$mid);
			$self->{FAM}{PARENT_NODE}{$fam}{$_} = [$fid,$mid];								
		}

		### ( bzw FOUNDER Status )
		elsif ( ! $fid && ! $mid  )  { $self->{FAM}{FOUNDER}{$fam}{$sid} = 1 }
		else { push @er, "Error in line - father or mother must not be zero: @$l\n"; next }

		### individuals gender
		$self->{FAM}{SID2SEX}{$fam}{$sid} = $sex;

		### individuals affection status
		$aff = 0 if $aff =~ /^x$/i;
		$self->{FAM}{SID2AFF}{$fam}{$sid} = $aff;

		### sibs and mates
		if ($fid) { 
			$self->{FAM}{SIBS}{$fam}{$fid . '==' . $mid}{$sid} = 1;
		}
		
		### Sample ID
		if (! $self->{FAM}{PID}{$fam}{$sid} ) {
			$self->{FAM}{PID}{$fam}{$sid} = 1;
		}
		else { push @er, "Individual $sid is duplicated!\n" }
		
		my %cit = (
			0 => 'IS_DECEASED', 1 => 'IS_SAB_OR_TOP', 2 => 'IS_PROBAND', 3 => 'IS_ADOPTED', 
			4 => 'ARE_TWINS', 5 => 'ARE_CONSANGUINEOUS', 6 => 'INNER_SYMBOL_TEXT', 7 => 'SIDE_SYMBOL_TEXT'
		);
		
		### sid information that are just stored without major processing at this point
		for (0 .. 4) {
			if ($sample_info[$_]) {
				$self->{FAM}{$cit{$_}}{$fam}{$sid} = $sample_info[$_]				
			}
		}
		
		### INNER_SYMBOL_TEXT and SIDE_SYMBOL_TEXT is just stored
		$self->{FAM}{$cit{6}}{$fam}{$sid} = $sample_info[6] if defined $sample_info[6];				
		$self->{FAM}{$cit{7}}{$fam}{$sid} = $sample_info[7] if defined $sample_info[7];				
		
		### storing twin information for later processing
		if ($sample_info[4]) { $twins{$sample_info[4]}{$sid} = 1 }
		
		### storing consanguine information for later processing
		if ($sample_info[5]) { $consang{$sample_info[5]}{$sid} = 1 }
		
		### storing further case information. They will appear as symbol upper text later		
		for (8 .. 11) {			
			my $col_nr = $_-6;
			my $name = 'Case_Info_' . $col_nr;
			$ci->{PID}{$sid}{$name} = $sample_info[$_];
			$ci->{COL_TO_NAME}{$col_nr} = $name;
			$ci->{COL_NAMES}{$name} = 1;
			$self->{FAM}{CASE_INFO_SHOW}{$fam}{$col_nr} = 1 if defined $sample_info[$_];		
		}
	}

	### some checks ...
	### gender of parents	
	foreach my $sid ( keys % { $self->{FAM}{SID2FATHER}{$fam} } ) {
		my $sid_old = $ci->{PID}{$sid}{Case_Info_1};
		my $fid = $self->{FAM}{SID2FATHER}{$fam}{$sid};
		if ( !$self->{FAM}{PID}{$fam}{$fid}) {
			my $fid_old =  $ci->{PID}{$fid}{Case_Info_1};
			push @er,  "Individual $fid_old is declared as father of $sid_old but there are no other information from $fid_old found!\n";
		}	
	}
	
	foreach my $sid ( keys % { $self->{FAM}{SID2MOTHER}{$fam} } ) {
		my $sid_old = $ci->{PID}{$sid}{Case_Info_1};
		my $mid = $self->{FAM}{SID2MOTHER}{$fam}{$sid};
		if ( !$self->{FAM}{PID}{$fam}{$mid}) {
			my $mid_old =  $ci->{PID}{$mid}{Case_Info_1};
			push @er,  "Individual $mid_old is declared as mother of $sid_old but there are no other information from $mid_old found!\n";
		}	
	}
	
	foreach my $sid ( keys % { $self->{FAM}{SID2FATHER}{$fam} } ) {
		my $sid_old = $ci->{PID}{$sid}{Case_Info_1};
		my $fid = $self->{FAM}{SID2FATHER}{$fam}{$sid};
		my $fid_old = $ci->{PID}{$fid}{Case_Info_1};
		push @er,  "Gender of individual $fid_old should be male, because it has been declarated as father of $sid_old.\n" if defined $self->{FAM}{SID2SEX}{$fam}{$fid} && $self->{FAM}{SID2SEX}{$fam}{$fid} ne '1'	
	}
	foreach my $sid ( keys % { $self->{FAM}{SID2MOTHER}{$fam} } ) {
		my $sid_old = $ci->{PID}{$sid}{Case_Info_1};
		my $mid = $self->{FAM}{SID2MOTHER}{$fam}{$sid};
		my $mid_old = $ci->{PID}{$mid}{Case_Info_1};
		push @er,  "Gender of individual $mid_old should be female, because it has been declarated as mother of $sid_old.\n" if defined $self->{FAM}{SID2SEX}{$fam}{$mid} && $self->{FAM}{SID2SEX}{$fam}{$mid} ne '2'
	}
	### founder without children
	foreach my $founder ( keys % { $self->{FAM}{FOUNDER}{$fam} } ) {
		my $founder_old = $ci->{PID}{$founder}{Case_Info_1};
		push @er,  "Founder individual $founder_old has no children.\n" unless keys %{ $self->{FAM}{CHILDREN}{$fam}{$founder} }
	}
	
	### twins check and storage
	if (%twins) {
		N1:foreach my $k (keys %twins) {
			my @twins = keys %{$twins{$k}} or next;
			if (scalar @twins == 1) {
				my $sib_old = $ci->{PID}{$twins[0]}{Case_Info_1};
				push @er,  "The twin individual $sib_old has no counterpart(s).\n"; next N1
			}
			
			my ($twt, $id) = $k =~ /^(.)_(.+)$/; ### match already proved in RedPed
			$twt = lc $twt;
									
			### are twins truly siblings?
			my ($par, $gender);
			N2:foreach my $sib (@twins) {
				my $sib_old = $ci->{PID}{$sib}{Case_Info_1};
				### twins should not be declared as founder
				if (! $self->{FAM}{SID2FATHER}{$fam}{$sib}) {
					push @er,  "The twin individual $sib_old must not be a founder.\n"; next N1
				}
				$par = $self->{FAM}{SID2FATHER}{$fam}{$sib} . '==' .  $self->{FAM}{SID2MOTHER}{$fam}{$sib} if ! $par;
				$gender = $self->{FAM}{SID2SEX}{$fam}{$sib} if ! $gender;
				### twins should be siblings
				if (! $self->{FAM}{SIBS}{$fam}{$par}{$sib}) {
					push @er,  "The twin individual $sib_old is not a member of the sibling group.\n"; next N1
				}
				### monozygotic twins schould have same gender
				if (( $twt eq 'm') && $self->{FAM}{SID2SEX}{$fam}{$sib} != $gender) {
					push @er,  "The twin individual $sib_old is declared as monozygotic but differs in gender of other twins.\n"; next N1
				}
			
				### store twin information
				$self->{FAM}{SID2TWIN_GROUP}{$fam}{$sib} = $k;
				$self->{FAM}{TWIN_GROUP2SID}{$fam}{$k}{$sib} = 1;
				$self->{FAM}{SID2TWIN_TYPE}{$fam}{$sib} = $twt;
			}						
		}
	}
	
	###consanguine check and storage
	if (%consang) {
		foreach my $k (keys %consang) {
			my @cons = keys %{$consang{$k}} or next;
			@_ = (); foreach (@cons) { push @_, $ci->{PID}{$_}{Case_Info_1} }
			$_ = join ',',@_;
			if (scalar @cons != 2) {
				push @er,  "A consanguinity group can only contain two individuals: $_!"; next
			}
			if (! $self->{FAM}{CHILDREN_COUPLE}{$fam}{$cons[0]}{$cons[1]}) {
				push @er,  "You declared individuals: $_ as consanguineous but they have no offspring!"; next
			}
			
			$self->{FAM}{CONSANGUINE_MAN}{$fam}{$cons[0]}{$cons[1]} = 1;
			$self->{FAM}{CONSANGUINE_MAN}{$fam}{$cons[1]}{$cons[0]} = 1;
		}		
	}
	
	### errors were found -> roll back actions and warn
	if (@er) {
		$self = thaw($param->{SELF_BACKUP}) if $param->{SELF_BACKUP};
		undef $param->{SELF_BACKUP};
		if (scalar @er < 20) { 
			$er .= $_ foreach @er;	
			ShowInfo("There are errors in family $fam!\n\n$er", 'error'); return undef 
		}
		else {
			for ( 0 .. 19 ) { $er .= $er[$_] }
			ShowInfo("There are too many errors in family $fam - only some of them are shown!\n\n$er", 'error'); return undef 
		}
	}
	
	### temporary
	#foreach my $l (@{$self->{FAM}{PED_ORG}{$fam}}) {
	#	next unless $l;
	#	$l->[13] = $self->{FAM}{PID2PIDNEW}{$fam}{$l->[0]};	
	#	$ci->{PID}{$l->[13]}{'Case_Info_2'} = $l->[13];
	#	$self->{FAM}{CASE_INFO_SHOW}{$fam}{2} = 1 ;		
	#}
	
	1;
}


#==================
sub ShuffleColors {
#==================	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	return unless $fam;
	
	return if  ! $self->{FAM}{HAPLO} || ! $self->{FAM}{HAPLO}{$fam} || ! keys % { $self->{FAM}{HAPLO}{$fam}{PID} };
	my %t;
	my %s = ( $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam} => 1, 'NI-0' => 1, 'NI-1' => 1, 'NI-2' => 1, 'NI-3' => 1 );
	### which colors are there  ?
	foreach my $p (keys %{$self->{FAM}{PID}{$fam}}) {
		next unless $self->{FAM}{HAPLO}{$fam}{PID}{$p};
		foreach my $mp ( 'M', 'P' ) {
			foreach (@ { $self->{FAM}{HAPLO}{$fam}{PID}{$p}{$mp}{BAR} }) {
				$s{@$_[1]} = 1 if $self->{FAM}{HAPLO}{$fam}{PID}{$p}{$mp}{SAVE};
				$t{@$_[1]} = @$_[1]
			}
		}
	}

	### make new haplotype colors
	foreach (keys %t) {
		if (! $s{$_} ) {
			$t{$_} = sprintf("#%02x%02x%02x", int(rand(256)),int(rand(256)),int(rand(256)));
		}
	}

	### write back colors
	foreach my $p (keys %{$self->{FAM}{PID}{$fam}}) {
		next unless $self->{FAM}{HAPLO}{$fam}{PID}{$p};
		foreach my $mp ( 'M', 'P' ) {
			foreach  (@ { $self->{FAM}{HAPLO}{$fam}{PID}{$p}{$mp}{BAR} }) {
				@$_[1] = $t{@$_[1]}
			}
		}
	}
}


### codes for genotypes:
### I   : informative genotype
### NI-0: completely lost haplotype
### NI-1: unique lost genotype
### NI-2: genotype OK + 'by hand' declared as non-informative
### NI-3: genotype OK +  automatic declared as non-informative
#=========================
sub ShuffleFounderColors {
#=========================
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	return unless $fam;
	
	return unless $self->{FAM}{HAPLO}{$fam};
	return unless keys %{ $self->{FAM}{HAPLO}{$fam}{PID} };
			
	my $h = $self->{FAM}{HAPLO}{$fam}{PID};
	my $un = $self->{FAM}{HAPLO_UNKNOWN}{$fam};
	my $huc = $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam};

	my @founder = keys %{$self->{FAM}{FOUNDER}{$fam}} or return undef;

	### clear all color information of founder bars
	foreach my $pid (keys %{$self->{FAM}{PID}{$fam}}) {
		next unless defined $h->{$pid};
		undef $h->{$pid}{M}{BAR} unless $h->{$pid}{M}{SAVE};
		undef $h->{$pid}{P}{BAR} unless $h->{$pid}{P}{SAVE};
	}

	### declare founder
	my $c = scalar @{ $self->{FAM}{MAP}{$fam}{MARKER} } ;
	foreach my $p (@founder) {
		if ( $h->{"$p"} ) {
			foreach my $m ( 'M' , 'P' ) {
				next unless $h->{$p}{$m};
				next if $h->{$p}{$m}{SAVE};  
				$h->{$p}{$m}{HIDE} = 0;
				my $co = sprintf("#%02x%02x%02x", int(rand(256)),int(rand(256)),int(rand(256)));
				my $flag; for ( 1 .. $c ) {
					my $al = $h->{"$p"}{$m}{TEXT}[$_-1];
					if ($al eq $un) {
						push @{$h->{"$p"}{$m}{BAR}}, [ 'NI-1', $co ]
					}
					else {
						push @{$h->{"$p"}{$m}{BAR}}, ['I', $co ] ; $flag = 1
					}
				}
				unless ($flag) {
					foreach (@{$h->{"$p"}{$m}{BAR}}) { @$_[0] = 'NI-0' }
				}
			}
		}
	}
	1;
}

# Processing haplotype blocks
#======================
sub ProcessHaplotypes {
#======================
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	return unless $fam;
	
	return unless $self->{FAM}{HAPLO}{$fam};
	return unless $self->{FAM}{HAPLO}{$fam}{PID};

	my $h = $self->{FAM}{HAPLO}{$fam}{PID};
	my $s = $self->{FAM}{STRUK}{$fam};
	
	### delete everything instaed of founder
	foreach my $pid (keys %{$self->{FAM}{PID}{$fam} }) {
		next if $self->{FAM}{FOUNDER}{$fam}{$pid};
		next unless defined $h->{$pid};
		undef $h->{$pid}{P}{BAR};
		undef $h->{$pid}{M}{BAR};
	}
		
	###  derive haplotype colors
	W:while (1) {
		my $flag = 0;
		F:foreach my $pid (keys %{$self->{FAM}{PID}{$fam}}) {
			next if $self->{FAM}{FOUNDER}{$fam}{$pid};
			next unless $h->{$pid};
			### still no haplotype derived
			if (! $h->{$pid}{P}{BAR} || ! $h->{$pid}{M}{BAR} ) {
				next if ! $h->{$pid}{M}{TEXT} || ! $h->{$pid}{P}{TEXT};
				
				### duplicate color information from duplicated pids
				if ($self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$pid}) {
					my $orig_pid = $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$pid};					
					if ($h->{$orig_pid}{P}{BAR} && $h->{$orig_pid}{M}{BAR}) {
						foreach ( @ { $h->{$orig_pid}{P}{BAR} } ) { push @ { $h->{$pid}{P}{BAR} }, [ @$_ ] }
						foreach ( @ { $h->{$orig_pid}{M}{BAR} } ) { push @ { $h->{$pid}{M}{BAR} }, [ @$_ ] }					
						next;
					}
					else { next }										
				}							
				
				my ($p, $m) = ( $self->{FAM}{SID2FATHER}{$fam}{$pid}, $self->{FAM}{SID2MOTHER}{$fam}{$pid} );
				if ( $h->{$p}{P}{TEXT} && $h->{$p}{M}{TEXT} ) {
					if ( ! $h->{$p}{P}{BAR} || ! $h->{$p}{M}{BAR}) {  $flag = 1 }
					else {
						my $a = $h->{$pid}{P}{TEXT};
						### BARs + ALLELE from father
						my ($aa1, $aa2) = ( $h->{$p}{P}{TEXT}, $h->{$p}{M}{TEXT} );
						my ($ba1, $ba2) = ( $h->{$p}{P}{BAR},  $h->{$p}{M}{BAR} );
						$h->{$pid}{P}{BAR} = CompleteBar($fam,$a, $aa1, $ba1, $aa2, $ba2);												
					}
				} else {
					ShowInfo("The file seemes to be corrupted - missing haplotype for $pid ?\n",'error');
					delete $self->{FAM}{HAPLO}{$fam};
					delete $self->{FAM}{HAPLO}{$fam};
					return undef
					
				}

				if ( $h->{$m}{P}{TEXT} && $h->{$m}{M}{TEXT} ) {
					if (! $h->{$m}{P}{BAR} || ! $h->{$m}{M}{BAR}) {  $flag = 1 }
					else {
						my $b = $h->{$pid}{M}{TEXT};
						### BARs + ALLELE from mother
						my ($ba3, $ba4) = ( $h->{$m}{P}{BAR},  $h->{$m}{M}{BAR} );
						my ($aa3, $aa4) = ( $h->{$m}{P}{TEXT}, $h->{$m}{M}{TEXT} );
						$h->{$pid}{M}{BAR} = CompleteBar($fam,$b, $aa3, $ba3, $aa4, $ba4);
					}
				} else {
					ShowInfo("The file seemed to be corrupted - missing haplotype for $m ?\n",'error');

					delete $self->{FAM}{HAPLO}{$fam};
					return undef
				}
			}
		}
		last W unless $flag;
	}
	1;
}

#================
sub CompleteBar {
#================	
	my ($fam,$a, $aa1, $ba1, $aa2, $ba2) = @_;
	return undef if ! $ba1 || ! $ba2 || ! @$ba1 || ! @$ba2;

	my ($phase, @bar);
	my $un = $self->{FAM}{HAPLO_UNKNOWN}{$fam};
	my $unc = $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam};

	### Phase ist nicht definiert -> Vorr�cken bis zur ersten informativen Stelle
	### und Phase danach definieren
	for (my $j = 0; $j < scalar @$a; $j++) {
		next if @$aa1[$j] eq @$aa2[$j];
		if (@$a[$j] eq @$aa1[$j]) { $phase = 1 } else { $phase = 2 } last
	}
	### wenn das fehlschlaegt ist der Ganze Haplotyp fuer die Katz
	unless ($phase) {
		push @bar, [ 'NI-0', $unc ] foreach @$a;
		return \@bar
	}

	for (my $i = 0; $i < scalar @$a; $i++) {
		### nicht informative Stelle -> entweder Haplotyp fortfuehren
		### oder, wenn voreingestellt als uninformativ deklarieren
		if (@$a[$i] eq $un) {
			if    ($phase == 1) { push @bar, [ 'NI-1', $$ba1[$i][1] ]	 }
			elsif ($phase == 2) { push @bar, [ 'NI-1', $$ba2[$i][1] ]	 }
		}
		elsif ( (@$aa1[$i] eq @$aa2[$i])  ) {
			if    ($phase == 1) { push @bar, [ 'NI-3', $$ba1[$i][1] ]	 }
			elsif ($phase == 2) { push @bar, [ 'NI-3', $$ba2[$i][1] ]	 }
		}
		else {
			if (@$a[$i] eq @$aa1[$i]) { push @bar, [ 'I', $$ba1[$i][1] ]; $phase = 1 }
			else { push @bar, [ 'I', $$ba2[$i][1] ]; $phase = 2 }
		}
	}
	return \@bar;
}


# Which founder couple come to the family in which generation ?
#============
sub FindTop {
#============
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my (%Top, $f, $m, $flag);
	P:foreach my $partner ( keys % { $self->{FAM}{SIBS}{$fam} } ) {
		($f, $m) = split '==', $partner;
		
		## find everybody joined in couple group  
		my %P = ( $f => 1, $m => 1);
		W:while (1) {
			undef $flag;
			foreach my $p ( keys %P ) {
				foreach my $c ( keys % { $self->{FAM}{COUPLE}{$fam}{$p} }) {
					if (! $P{$c} ) {$P{$c} = 1; $flag = 1}
				}
			}
			last W unless $flag
		}
			
		foreach my $s (keys %P) {
			foreach	(keys % { $self->{FAM}{COUPLE}{$fam}{$s} } ) {
				if ( (! $self->{FAM}{FOUNDER}{$fam}{$_}) && (! $self->{FAM}{CHILDREN}{$fam}{$s}{$_} ) && ! $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$_} ) {
					next P
				}
			}
		}
		
		if ( 
		((defined $self->{FAM}{FOUNDER}{$fam}{$f} or (defined $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$f}))) and 
		((defined $self->{FAM}{FOUNDER}{$fam}{$m} or (defined $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$m})))
		) {
			my @TOP = ($f,$m);
			ChangeOrder(\@TOP) if ! $param->{SORT_COUPLE_BY_GENDER};
			$Top{$partner} = [ @TOP ];
			$self->{FAM}{STRUK}{$fam} = 	[
									[
										[
											[
												[  @TOP  ],
												[ [@TOP] ],
												[ [@TOP] ],
											]
										]
									]
								];

		}
	}
	
	### are there no founders ? ---> ERROR
	@_ = keys %Top;
	if (! @_) {
		 ShowInfo("There is no founder couple in this family !\nFurther drawing aborted.", 'error'); 
		 return undef;
	}

	### Which founder belong to which generation ??
	### If there are more then one founder couple, this method examine with help of BuildStruk()
	### separate sub family structures and searches for connecting overlapping peoples
	### In some situations this has been shown to fail, future work !
	if ($#_) {
		my %G2P;
		foreach my $c ( sort keys %Top ) {
			$self->{FAM}{STRUK}{$fam} = [
								[
									[
										[
											[ @{$Top{$c}}],
											[$Top{$c} ],
											[$Top{$c} ],
										]
									]
								]
							] ;
			
			$self->{GLOB}{STRUK_MODE} = 1;
			BuildStruk($fam);
			$self->{GLOB}{STRUK_MODE} = 0;
			my $s = $self->{FAM}{STRUK}{$fam};
			### extract persons for each generation
			my $g = 0;
			foreach my $G (@$s) {
				foreach my $S (@$G) {
					foreach my $P (@$S) {
						if ( ref $P ) {							
							foreach my $p ( @{$P->[0]} ) { 
								$p = $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p} if  $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$p};
								$G2P{$c}{$g}{$p} = 1 
							}
						} else {  
							$P = $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$P} if  $self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$P};
							$G2P{$c}{$g}{$P} = 1 
						}
					}
				} $g++
			}
		}

		### find individual intersection and generation relationship
		my %calc;
		C1:foreach my $c1 ( keys %G2P ) {
			foreach my $G1 ( keys %{$G2P{$c1} } ) {
				foreach my $p1 ( keys %{$G2P{$c1}{$G1} } ) {
					C2:foreach my $c2 ( keys %G2P ) {
						next if $c2 eq $c1;
						foreach my $G2 ( keys %{$G2P{$c2} } ) {
							foreach my $p2 ( keys %{$G2P{$c2}{$G2} } ) {
								if ($p1 eq $p2) {
									if (! %calc) {
										$calc{$G1}{$c1} = 1;
										$calc{$G2}{$c2} = 1;
									} else {
										foreach my $g ( keys %calc ) {
											if ($calc{$g}{$c1}) {
												my $diff = $g-$G1;
												$calc{$G2+$diff}{$c2} = 1
											}
											if ($calc{$g}{$c2}) {
												my $diff = $g-$G2;
												$calc{$G1+$diff}{$c1} = 1
											}
										}
									}
									next C2
								}
							}
						}
					}
				}
			}
		}
		
		### declaration of founder/generation
		my %save2;
		my ($max) =  sort { $b <=> $a } keys %calc;
		foreach my $g (sort { $b <=> $a } keys %calc) {
			foreach my $c (keys % { $calc{$g} }) {
				if (! $save2{$c}) {
					$self->{FAM}{FOUNDER_COUPLE}{$fam}{$max-$g}{$c} = 1;
					$save2{$c} = 1
				}
			}
		}
		### Sollte eigentlich nicht mehr vorkommen ... 
		unless ($self->{FAM}{FOUNDER_COUPLE}{$fam}{0}) {
			ShowInfo("There is no founder couple in generation 1 !",'error');
			return undef;
		}
		
		### multiple mates can be cleared ... see method SetCouple()
		my %save;
		foreach my $g ( keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam} } ) {
			foreach my $coup ( keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam}{$g} } ) {
				my ($p1, $p2) = split '==', $coup;			
				my %P = ( $p1 => 1, $p2 => 1);
				W:while (1) {
					undef $flag;
					foreach my $p ( keys %P ) {
						foreach my $c ( keys % { $self->{FAM}{COUPLE}{$fam}{$p} }) {
							if (! $P{$c} ) {$P{$c} = 1; $flag = 1}
						}
					}
					last W unless $flag
				}
				foreach (keys %P) { 
					if ($save{$_}) {delete $self->{FAM}{FOUNDER_COUPLE}{$fam}{$g}{$coup} } 
					else { $save{$_} = 1 }								
				}								
			}
		}
		### work arround for special case of multiple couple group which is deleted for generation 0
		if (keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam} } && ! keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam}{0} }) {
			my $lg;
			foreach my $g (sort { $a <=> $b } keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam} }) {
				if (keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam}{$g} }) {
					$lg = $g if ! defined $lg;
					$self->{FAM}{FOUNDER_COUPLE}{$fam}{$g-$lg} = $self->{FAM}{FOUNDER_COUPLE}{$fam}{$g};
					delete $self->{FAM}{FOUNDER_COUPLE}{$fam}{$g}
				}
				
			}
		}		
		
		### set up founder couples in {STRUK}
		$self->{FAM}{STRUK}{$fam} = [[]];
		my $s = $self->{FAM}{STRUK}{$fam}[0];
		my @couples = keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam}{0} };	
		foreach (@couples) {
			my ($p1, $p2) = split '==', $_;
			($p1, $p2) = ($p2, $p1) if int(rand(2));
			my $Next_S = [];
			push @$s, $Next_S;
			if (scalar (keys % { $self->{FAM}{COUPLE}{$fam}{$p1} }) > 1) { push @$Next_S, SetCouples($fam,$p1) }
			else { push @$Next_S, SetCouples($fam,$p2) }
		}
	}
	1;
}

### change order of elements in an array
### input=output= reference to array
#================
sub ChangeOrder {
#================	
	my $array = shift;
	return if ! $array || ! @$array;
	return if scalar @$array == 1;
	my $fam = $self->{GLOB}{CURR_FAM};
	### do not mix this array but sort it by Case_Info_1
	if ($param->{SORT_BY_PEDID}) {
		my %s; foreach (@$array) {		
			$s{$self->{FAM}{CASE_INFO}{$fam}{PID}{$_}{'Case_Info_1'}} = $_
		}
	
		@$array = ();
		foreach (nsort keys %s) {push @$array, $self->{FAM}{PID2PIDNEW}{$fam}{$_} }

	}
	### mix this array 
	else {
		for (my $i = @$array; --$i; ) {
			my $j = int rand ($i+1);
			@$array[$i,$j] = @$array[$j,$i];
		}
	}
}



############################################################################
#  family specific variable $self->{$struk} as nested array of arrays of ...
#  holds pedigree structure Hierachy: Generation->Sibgroups->Person/Couples
#
#
#  $struk =
#  [
#     [ Generation 1 ],                generation
#     [ Generation 2 ],                
#     [                                
#        [ Sibs 1 ],                    extended sibgroup
#        [ Sibs 2 ],                   
#        [                             
#           Pid 1,                      sib without spouses
#           [ Partner 1 ],              sib with spouses
#           [                       
#              [ p1, p2, p3 ],          drawing order of multiple mates in one row
#              [ p1, p3 ] , [ p2, p3 ]  reflects sib groups drived from [ p1, p2, p3 ]
#              [ p1, p2 ] , [ p2, p3 ]  reflects *real* drawing order of sib groups
#           ]
#        ]
#     ]
#  ]
#
#
###########################################################################


#===============
sub BuildStruk {
#===============	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $G = 0;
	my $EndFlag = 1;
	my $s = $self->{FAM}{STRUK}{$fam};
	my $skip = {};
	my $skip2 = {};
	### clear generation from $G+1
	$#{$s}=0;
	while ($EndFlag) {
		my $Next_G = []; push @$s, $Next_G;
		undef $EndFlag;
		foreach my $S ( @ { $s->[$G] } ) {
			foreach my $P ( @$S ) {
				if ( ref $P ) {
					$EndFlag = 1;
					foreach my $p ( @ { $P->[1] } ) {					
						my @children; 
						foreach my $child (keys % { $self->{FAM}{CHILDREN_COUPLE}{$fam}{@$p[0]}{@$p[1]} }) {
							my $r = SetCouples($fam,$child);													
							if (ref $r) { 
								my $c = join '==', nsort @ { $r->[0] };
																																		
								my $founder = 0; 							
								foreach my $coupl ( @ { $r->[0] } ) { if (!$self->{FAM}{FOUNDER}{$fam}{$coupl}) { $founder++ } }
																							
								### checking if child must be skipped, because it belongs to a multiple mate node
								### and this node would be drawn multiple times depending from number of non-founders inside
								if (!$self->{GLOB}{STRUK_MODE} && ($founder >1)) {																	
									if ($skip->{$child} && ($skip->{$child} == ($founder-1))) { push @children, $child }								
									else { $skip->{$_}++ foreach @ { $r->[0] } }
								}
								else { 									
									push @children, $child if ! $skip2->{$child};
									$skip2->{$_}++ foreach @ { $r->[0] }
								}
							}
							else { push @children, $child }
						}
						
						ChangeOrder(\@children) if @children;
						my $Next_S = []; if (@children) { push @$Next_G, $Next_S }
						foreach my $child (@children) {
							$_ = SetCouples($fam,$child);
							push @$Next_S, $_ if $_;
						}
					}
				}
			}
		}
		### if there are new founder couples in that generation (see FindTop )
		### they have to be integrated as new starting point
		if (! $self->{GLOB}{STRUK_MODE} && $self->{FAM}{FOUNDER_COUPLE}{$fam}{$G+1}) {
			foreach ( keys % { $self->{FAM}{FOUNDER_COUPLE}{$fam}{$G+1} } ) {
				my ($p1) = split '==', $_;
				my $Next_S = [];			
				### new founder couple are randomly placed inside $Next_g	
				splice (@$Next_G, int(rand(scalar @$Next_G+1)), 0, $Next_S);
				push @$Next_S, SetCouples($fam,$p1);
			}
		}
		$G++;
	}
	pop @$s;
}


# Zeichen-Matrix anlegen. Von STRUK ausgehend werden die relativen Zeichenpositionen
# aller Personen generationsweise festgelegt (P2XY/YX2P)
# Next layer after {STRUK} is {MATRIX} -> translation into relative XY Positions
#================
sub BuildMatrix {
#================	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $s  = $self->{FAM}{STRUK}{$fam};
	$self->{FAM}{MATRIX}{$fam} = {};
	$self->{FAM}{PID_SAVE}{$fam} = {};
	my $mt = $self->{FAM}{MATRIX}{$fam};
	my $x = my $x0 = 0;
	my $y = my $y0 = 0;
	my $xs	= $self->{FAM}{X_SPACE}{$fam};
	my $ys	= $self->{FAM}{Y_SPACE}{$fam};
	my %save;
	
	### Zeichenmatrix anlegen
	foreach my $G (@$s) {
		foreach my $S (@$G) {
			foreach my $P (@$S) {
				if ( ref $P ) {
					foreach my $p ( @{$P->[0]} ) {
						next if $save{$p};
						$mt->{P2XY}{$p}   = { X => $x, Y => $y };
						$mt->{YX2P}{$y}{$x} = $p;
						$x+= $xs+1;
						$save{$p} = 1;
					}
				} else {
					next if $save{$P};				
					$mt->{P2XY}{$P}   = { X => $x, Y => $y };
					$mt->{YX2P}{$y}{$x} = $P;
					$x+= $xs+1;
					$save{$P} = 1;
				}
			}
		}
		$x = $x0;
		$y+= $ys
	}
}

### basic DBI support
#======================
sub ImportPedegreeDBI {
#======================
	
	my $d = $mw->Toplevel(-title => 'Database Connection');						
	my %T = ( qw / DB_TYPE 1 DB_HOST 1 DB_PORT 1 DB_RELATION 1 DB_SID 1 DB_UNAME 1 /);
	my %ped_org = ();	
		
	my $f1 = $d->Frame()->pack(-side => 'top',  -anchor => 'w', -fill => 'x');
	my $f2 = $d->Frame()->pack(-side => 'top',  -anchor => 'w', -fill => 'x');
	my $f3 = $d->Frame()->pack(-side => 'top',  -anchor => 'w', -fill => 'x');
	my $f4 = $d->Frame()->pack(-side => 'top',  -anchor => 'w', -fill => 'x');
	my $f5 = $d->Frame()->pack(-side => 'top',  -anchor => 'w', -fill => 'x');
	my $f6 = $d->Frame()->pack(-side => 'top',  -anchor => 'w', -fill => 'x');
	my $f7 = $d->Frame()->pack(-side => 'top',  -anchor => 'w', -fill => 'x');
	my $fb = $d->Frame()->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'x');
	
	### Connect bottom
	$fb->Button(-text => 'Connect', -width => 10, -command => sub {
		$d->destroy;
		my ($dbh, $colnames) = MakeDBConnection();
		
		unless ($dbh) { $canvas->Subwidget("canvas")->Tk::focus; return undef }
		
		my $ped_ref = $dbh->selectcol_arrayref("select distinct($colnames->[0]) from $self->{GLOB}{DB_RELATION} order by $colnames->[0]");
		if ($DBI::errstr) { ShowInfo($DBI::errstr); $dbh->disconnect; return undef}			
		 		
		### No pedigrees found, something is bad
		if (!@$ped_ref ) {
			ShowInfo("The relation $self->{GLOB}{DB_RELATION} seems not to contain any data!");
			$dbh->disconnect;
			return;
		}
				
		my $d2 = $mw->DialogBox(-title => 'Choose Pedigrees',-buttons => ['Ok', 'Cancel']);
		
		### Chosing Pedigrees from the listbox
		my $f1 = $d2->Frame->grid(-row => 1, -column => 0, -sticky => 'w');
		my $lab1 = $f1->Label(-text => 'Pedigree Selection', -width => 20)->pack(-side => 'top', -anchor => 'w');
		my $lb = $f1->Scrolled('Listbox',
			-scrollbars => 'osoe', -selectmode => 'extended', -selectbackground => 	'red',
			-height => 14, -width => 25, -exportselection => 0,
		)->pack(-side => 'top', -fill => 'both', -expand => 1);
		$d2->gridColumnconfigure( 0, -pad => 10);
		foreach (@$ped_ref) { $lb->insert('end',$_) }
				
		my $answ = $d2->Show();		
		if ($answ eq 'Cancel') { $dbh->disconnect; return }
		
		### processing 
		else {											
			my @ped; 
			foreach ($lb->curselection) { push @ped, $lb->get($_) }
			return unless @ped;
			foreach (@ped) { $_ = "'$_'" }
			my $choose = join ',', @ped;
			my $aref = $dbh->selectall_arrayref("select * from $self->{GLOB}{DB_RELATION} where $colnames->[0] in ($choose)");
			if ($DBI::errstr) { ShowInfo($DBI::errstr); $dbh->disconnect; return undef}			
			$dbh->disconnect();
			return unless @$aref;		

			### read the data in global Hash %pedigree
			foreach my $r (@$aref) {
				my $fam = shift @$r;
				push @{ $ped_org{$fam} }, [ @$r ];			
			}

			my $er = CheckPedigreesForErrors(\%ped_org, 'CSV');
			if ($er) { ShowInfo($er); return undef }
			
			### make a copy of $self to restore it in case of family processing errors
			$param->{SELF_BACKUP} = freeze($self);
			
			
			### Preeforming $self and preprocessing familys
			foreach my $fam (nsort keys %ped_org ) { 
				foreach (keys % { $self->{FAM} }) { delete $self->{FAM}{$_}{$fam} if $self->{FAM}{$_}{$fam}}
				AddFamToSelf($fam);
				$self->{FAM}{PED_ORG}{$fam} = $ped_org{$fam};
				ProcessFamily($fam) or return;
				FindLoops($fam);
				
				if (scalar keys % { $self->{FAM}{BREAK_LOOP_OK}{$fam} } > 3) {
					$self->{FAM}{LOOP_BREAK_STATUS}{$fam} = 2;
					foreach (keys % {$self->{FAM}{BREAK_LOOP_OK}{$fam} })  {
						$self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} = 1
					}	
				}	
			}
			
			### Updating Main Window menu
			my $fileref = $menubar->entrycget('View', -menu);
			my $drawref = $fileref->entrycget('Draw Pedigree ...', -menu);
			$drawref->delete(0,'end');
			for my $fam (nsort keys % { $self->{FAM}{PED_ORG} }) { 
				$drawref->add('command', -label => $fam, -command => sub {
					StoreDrawPositions();
					DrawOrRedraw($fam);
					RestoreDrawPositions()
				})
			}
			($self->{GLOB}{CURR_FAM}) = nsort keys % { $self->{FAM}{PED_ORG} };
			DoIt();
			
		}
	})->grid( -row => 0, -column => 0, -sticky => 'w');
	
	### Cancel bottom
	$fb->Button(-text => 'Cancel', -width => 10, -command => sub {
		$d->destroy();
	})->grid( -row => 0, -column => 1, -sticky => 'w');
	
	### Save Default bottom
	$fb->Button(-text => 'Save Default', -width => 10, -command => sub {
		open (FH, ">", "hp_dbi_default") or (ShowInfo("Unable to save current setting as default!\n$!"));
			foreach ( qw/ DB_TYPE DB_HOST DB_PORT DB_RELATION DB_SID DB_UNAME /) {
				print FH "$_=$self->{GLOB}{$_}\n" if $self->{GLOB}{$_}
			}
		close FH;
	})->grid( -row => 0, -column => 2, -sticky => 'w');
	
	### Load Default Bottom
	$fb->Button(-text => 'Load Default', -width => 10, -command => sub {		
		open (FH, "<", "hp_dbi_default") or (ShowInfo("Unable to load the default file:hp_dbi_default\n$!"));
			while (<FH>) {
				chomp;
				s/ //g;
				next unless $_;
				@_ = split "=",$_;
				if (@_ && (scalar @_==2) && $T{$_[0]}) {
					$self->{GLOB}{$_[0]} = $_[1];					
				}				
			}
		close FH;
	})->grid( -row => 0, -column => 3, -sticky => 'w');
		
	
	### BrowseEntry widget for Database Type
	$f1->Label(-text => 'Database type',-width => 13,-justify => 'left',-anchor => 'w',)->pack(-side => 'left');
	$f1->BrowseEntry(
		-textvariable => \$self->{GLOB}{DB_TYPE}, -choices => [ 'Oracle', 'PostgreSQL', 'MySQL' ],
		-bg => 'white',-disabledbackground => 'white',
		-width => 25, -state => 'readonly', -browsecmd => sub {
			if ($self->{GLOB}{DB_TYPE} =~ /Oracle/) 				{ $self->{GLOB}{DB_PORT} = 1521 }
			elsif ($self->{GLOB}{DB_TYPE} =~ /PostgreSQL/)	{ $self->{GLOB}{DB_PORT} = 5432 }
			elsif ($self->{GLOB}{DB_TYPE} =~ /MySQL/)			{ $self->{GLOB}{DB_PORT} = 3306 }
		}
	)->pack(-padx => 11, -side => 'left');
		
	
	$f2->Label(-text => 'Hostname',-width => 15,-justify => 'left',-anchor => 'w',)->pack(-side => 'left');
	my $entry2 = $f2->Entry(-textvariable => \$self->{GLOB}{DB_HOST},-width => 25)->pack( -side => 'left');
		
	$f3->Label(-text => 'Port',-width => 15,-justify => 'left',-anchor => 'w')->pack(-side => 'left');
	$f3->Entry(-textvariable => \$self->{GLOB}{DB_PORT},-width => 25)->pack( -side => 'left');
	
	$f4->Label(-text => 'Table name',-width => 15,-justify => 'left',-anchor => 'w')->pack(-side => 'left');
	$f4->Entry(-textvariable => \$self->{GLOB}{DB_RELATION},-width => 25)->pack( -side => 'left');
	
	$f5->Label(-text => 'DBname(SID)',-width => 15,-justify => 'left',-anchor => 'w')->pack(-side => 'left');
	$f5->Entry(-textvariable => \$self->{GLOB}{DB_SID},-width => 25)->pack( -side => 'left');
		
	$f6->Label(-text => 'Username',-width => 15,-justify => 'left',-anchor => 'w')->pack(-side => 'left');
	$f6->Entry(-textvariable => \$self->{GLOB}{DB_UNAME},-width => 25)->pack( -side => 'left');
	
	$f7->Label(-text => 'Password',-width => 15,-justify => 'left',-anchor => 'w')->pack(-side => 'left');
	$f7->Entry(-textvariable => \$self->{GLOB}{DB_PASSWD}, -show => '*',-width => 25 )->pack( -side => 'left');
				
	$d->withdraw();
	$d->Popup();	
	$d->idletasks;
	$d->iconimage($d->Photo(-format =>'gif',-data => GetIconData()));
	$d->grab();
}

#=====================
sub MakeDBConnection {
#=====================
	foreach ( qw/ DB_TYPE DB_HOST DB_PORT DB_RELATION  DB_UNAME DB_PASSWD/) {
		if (! $self->{GLOB}{$_}) {
			ShowInfo("There are missing values which are neded to establish a data base connection: $_"); return undef
		}
	}
	
	### prepare DNS string for DBI's connection method
	my ($dns, $dbh);
	if ($self->{GLOB}{DB_TYPE} =~ /oracle/i) { 
		$dns =  "dbi:Oracle:sid=$self->{GLOB}{DB_SID};host=$self->{GLOB}{DB_HOST};port=$self->{GLOB}{DB_PORT}";
	} 
	elsif ($self->{GLOB}{DB_TYPE} =~ /postgresql/i) { 
		$dns =  "dbi:PgPP:dbname=$self->{GLOB}{DB_SID};host=$self->{GLOB}{DB_HOST};port=$self->{GLOB}{DB_PORT}";
	}
	elsif ($self->{GLOB}{DB_TYPE} =~ /mysql/i) { 
		$dns =  "dbi:mysql:dbname=$self->{GLOB}{DB_SID};host=$self->{GLOB}{DB_HOST};port=$self->{GLOB}{DB_PORT}";
	}
	else {
		ShowInfo("Unknown data base type $self->{GLOB}{DB_TYPE} - must be (oracle, postgresql, mysql)"), return undef;
	}
	### connect to database and capture error messages
	eval { 
		$dbh = DBI->connect( $dns, $self->{GLOB}{DB_UNAME},$self->{GLOB}{DB_PASSWD}, { AutoCommit => 1, RaiseError => 0}) 
	};
	if ($@) {	ShowInfo($@);return undef }
	if ($DBI::errstr) { ShowInfo($DBI::errstr); return undef }
	
	### first statementhandle only to get column names
	my $sth = $dbh->prepare("select * from $self->{GLOB}{DB_RELATION}") or (ShowInfo($DBI::errstr), $dbh->disconnect, return undef);	
	if ($DBI::errstr) { ShowInfo($DBI::errstr);  $dbh->disconnect; return undef }
	
	$sth->execute;		
	if ($DBI::errstr) { ShowInfo($DBI::errstr);  $dbh->disconnect; return undef }
	
	my @names = @ { $sth->{NAME} };
	
	$sth->finish;
	
	### minimum of 6 columns are necessary
	if (scalar @names < 6) {  		
		ShowInfo("The relation $self->{DB_RELATION} does not complies with the requirements of at least 6 columns!");
		return;
	}
			
	return ($dbh,\@names);
}

#==================
sub ReadPedFromDB {
#==================
	my ($dbh, $fam, $col1) = @_ or return undef;
	my $aref = $dbh->selectall_arrayref("select * from $self->{GLOB}{DB_RELATION} where $col1 = '$fam'") or (ShowInfo($DBI::errstr), $dbh->disconnect, return undef);
	$dbh->disconnect();
	return unless @$aref;		
	
	### read the data in global Hash %pedigree
	my %ped_org;
	foreach my $r (@$aref) {
		my $fam = shift @$r;
		push @{ $ped_org{$fam} }, [ @$r ];			
	}
	
	my $er = CheckPedigreesForErrors(\%ped_org, 'CSV');
	if ($er) { ShowInfo($er); return undef }	
	
	AddFamToSelf($fam);
	$self->{FAM}{PED_ORG}{$fam} = $ped_org{$fam};
	ProcessFamily($fam);
	FindLoops($fam);
		
	if (scalar keys % { $self->{FAM}{BREAK_LOOP_OK}{$fam} } > 3) {
		$self->{FAM}{LOOP_BREAK_STATUS}{$fam} = 2;
		foreach (keys % {$self->{FAM}{BREAK_LOOP_OK}{$fam} })  {
			$self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} = 1
		}	
	}	
	1;
}


#==================
sub ImportPedfile {
#==================	
	my ($form, $f) = @_;
	if (!$f) { $f = $mw->getOpenFile() or return }
	ReadPed( -file => $f, -format => $form ) or return undef;
	($f) = fileparse($f, qr/\.[^.]*/);

	$self->{GLOB}{FILENAME} = "$f.hp";
	### Updating Main Window menu
	my $fileref = $menubar->entrycget('View', -menu);
	my $drawref = $fileref->entrycget('Draw Pedigree ...', -menu);
	$drawref->delete(0,'end');
	for my $fam (nsort keys % { $self->{FAM}{PED_ORG} }) { 
		$drawref->add('command', -label => $fam, -command => sub {
			StoreDrawPositions();
			DrawOrRedraw($fam);
			RestoreDrawPositions()
		}) 
	}

	($self->{GLOB}{CURR_FAM}) = nsort keys % { $self->{GLOB}{IMPORTED_PED} };
	DoIt();
}

#===================
sub DrawNextFamily {
#===================
	my @fam = nsort keys % { $self->{FAM}{PED_ORG} } or return;
	return if scalar @fam ==1;
	for (my $i=0; $i < scalar @fam; $i++) {
		if ($self->{GLOB}{CURR_FAM} eq $fam[$i]) {			
			StoreDrawPositions();			
			if (shift) { return if ! $i; $_ = $fam[$i-1] }
			else {  return if ! $fam[$i+1]; $_ = $fam[$i+1] }		
			DrawOrRedraw($_);
			RestoreDrawPositions();
			last;
		}		
	}
}

#====================
sub ImportHaplofile {
#====================	
	return unless keys % { $self->{FAM}{PED_ORG} };
	my ($format, $f) = @_;
	if (!$f) { $f = $mw->getOpenFile() or return }
	ReadHaplo( -file => $f, -format => $format ) or return;
	DuplicateHaplotypes();	
}

#==================
sub ImportMapfile {
#==================	
	return unless $self->{GLOB}{CURR_FAM};
	my $f = $mw->getOpenFile() or return;
	ReadMap( -file => $f, -format => shift ) or return;
	RedrawPed();
	AdjustView();
}

#=========
sub Zoom {
#=========	
	shift @_ if Exists ($_[0]);
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my ($ori, $flag, $x_screen, $y_screen) = @_;

	if ($ori == 1 ) {	for ($self->{FAM}{ZOOM}{$fam}, $self->{GLOB}{X_CANVAS}, $self->{GLOB}{Y_CANVAS}) { $_*=1.5 }}
	else {  for ($self->{FAM}{ZOOM}{$fam},$self->{GLOB}{X_CANVAS}, $self->{GLOB}{Y_CANVAS}) { $_/=1.5 } }	
		
	RedrawPed($fam);			
	
	if ($flag) { AdjustView(-fit => 'to_button') }
	else { AdjustView() }
}

#=======================
sub ReSetHaploShuffle {
#=======================	
	ShuffleColors();
	RedrawPed();
}

#==============
sub ShowAbout {
#==============	
	$mw->messageBox(
		-title => 'About HaploPainter', -message =>
		"Author: Holger Thiele\n" .
		"Version: $self->{GLOB}{VERSION} \n" .
		"Date: $param->{LAST_CHANGE}\n" .
		"Contact: hthiele\@users.sourceforge.net\n" .
		"Manual: http:\/\/haplopainter.sourceforge.net\n" ,		
		-type => 'OK', -icon => 'info'
	)		
}

#=================
sub OptionsPrint {
#=================
		
	my $d = $mw->DialogBox(-title => 'Page Settings',-buttons => ['Ok']);
	my $f = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');

	foreach my $s (
		[ 'BORDER',    'Margin [mm]',         0,0,   0,  100,    5  ],
		[ 'RESOLUTION_DPI',   'Resolution [dpi]',  1,0,   72,  600,    4  ],
	) {
		$f->Scale(
			-label  => @$s[1], -variable => \$self->{GLOB}{@$s[0]},
			-from   => @$s[4], -to => @$s[5],-orient => 'horizontal',
			-length => 150, -width => 12, -resolution => @$s[6],-command => sub {
			}
		)->grid( -row => @$s[2], -column => @$s[3], -sticky => 'w');
	}
	
	my $be3 = $f->BrowseEntry(
		-label => 'Orientation: ',-variable => \$self->{GLOB}{ORIENTATION},
		-width => 15,-choices =>	[ 'Landscape', 'Portrait' ], -labelPack => [ -side => 'top', -anchor => 'w' ],
	)->grid(-row => 3, -column => 0, -sticky => 'w', -padx => 4, -pady => 10);

	my $be4 = $f->BrowseEntry(
		-label => 'Paper Size: ',-variable => \$self->{GLOB}{PAPER}, -labelPack => [ -side => 'top', -anchor => 'w' ],
		-width => 15,-choices =>	[ nsort keys %{$param->{PAPER_SIZE}} ],
	)->grid(-row => 3, -column => 1, -sticky => 'w', -padx => 4, -pady => 10);

	$d->Show();
}

#=======================
sub OptionsConsanguine {
#=======================
	if (! $self->{GLOB}{CURR_FAM}) { 
		ShowInfo("You have to load any pedigree first to change settings!", 'info'); return 
	}	
	my $fam = $self->{GLOB}{CURR_FAM};
	my $freeze = freeze($self);
	
	my $d = $mw->Toplevel(-title => "Configuration for family $self->{GLOB}{CURR_FAM}");						
	$d->withdraw();
	
	my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -side => 'top', -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
	my $f2 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -side => 'top', -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
 	
	### Buttons on bottom
	$f2->Button(-text => 'Ok', -width => 10, -command => sub {
		RedrawPed();$d->destroy;
	})->grid( -row => 0, -column => 0, -sticky => 'w');
	
	$f2->Button(-text => 'Cancel', -width => 10, -command => sub {
		$self = thaw($freeze);$d->destroy;RedrawPed()
	})->grid( -row => 0, -column => 1, -sticky => 'w');
				
		
	$f2->Button(-text => 'Preview', -width => 10, -command => sub {
		RedrawPed()
	})->grid( -row => 0, -column => 3, -sticky => 'w');
	
	
	### choose PIDs for Loop break
	$f1->Label(-text => '  Select consanguineous couples', -width => 20)->pack(-side => 'top', -anchor => 'n');
	my $lb = $f1->Scrolled('Listbox',
		-scrollbars => 'osoe', -selectmode => 'extended', -selectbackground => 	'red',
		-height => 14, -width => 25, -exportselection => 0
	)->pack(-side => 'top', -fill => 'both', -expand => 1);
	
	my @nodes = nsort keys % { $self->{FAM}{PARENT_NODE}{$fam} };
	foreach (@nodes) {
		my ($p1, $p2) = split '==', $_;
		$p1= $self->{FAM}{CASE_INFO}{$fam}{PID}{$p1}{'Case_Info_1'};
		$p2= $self->{FAM}{CASE_INFO}{$fam}{PID}{$p2}{'Case_Info_1'};
		$_ = join '==', nsort ($p1,$p2);
	}
	$lb->insert('end', @nodes);
	
	for (my $i = 0; $i < scalar @nodes; $i++) {	
		my ($p1, $p2) = split '==', $lb->get($i);
		$p1=$self->{FAM}{PID2PIDNEW}{$fam}{$p1};
		$p2=$self->{FAM}{PID2PIDNEW}{$fam}{$p2};
		if ($self->{FAM}{CONSANGUINE_MAN}{$fam}{$p1}{$p2} ) {
			$lb->selectionSet($i);			
		}
		else {$lb->selectionClear($i) }
	}
	
	$lb->bind('<ButtonRelease-1>' => sub {								
		undef $self->{FAM}{CONSANGUINE_MAN}{$fam};
		foreach ($lb->curselection()) { 
			my ($p1, $p2) = split '==', $lb->get($_);
			$p1=$self->{FAM}{PID2PIDNEW}{$fam}{$p1};
			$p2=$self->{FAM}{PID2PIDNEW}{$fam}{$p2};
			$self->{FAM}{CONSANGUINE_MAN}{$fam}{$p1}{$p2} = 1;
			$self->{FAM}{CONSANGUINE_MAN}{$fam}{$p2}{$p1} = 1;
		}												
	});
	
	$d->Popup();	
	$d->idletasks;
	$d->iconimage($d->Photo(-format =>'gif',-data => GetIconData()));
	
	### to prevent manipulation from main wain window prior updated defaults 
	$d->grab	
}

#=====================
sub OptionsLoopBreak {
#=====================	
	if (! $self->{GLOB}{CURR_FAM}) { 
		ShowInfo("You have to load any pedigree first to change settings!", 'info'); return 
	}	
	my $fam = $self->{GLOB}{CURR_FAM};
	my $s = $self->{FAM}{LOOP}{$fam};
	my $b = $self->{FAM}{BREAK_LOOP_OK}{$fam};  
	my $freeze = freeze($self);
	my $nr_loops = scalar keys %$b;
	
	my ($lb6, $flag);
	
	my $d = $mw->Toplevel(-title => "Breaking loops ...");						
	$d->withdraw();
	
	my $f1 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -side => 'top', -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
	my $f2 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -side => 'top', -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
 	my $f3 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -side => 'top', -padx => 5, -pady => 5, -expand => 1, -fill => 'both');	
	
	### Buttons on bottom
	$f3->Button(-text => 'Ok', -width => 10, -command => sub {
		if ($flag) {	
			foreach my $k ( keys % { $self->{FAM} } ) {
				undef $self->{FAM}{$k}{$fam} if ! defined $def->{FAM}{$k};
			}
			ProcessFamily() or return undef;
			FindLoops();		
			DoIt();
		}	
		$d->destroy;
	})->grid( -row => 0, -column => 0, -sticky => 'w');
	
	$f3->Button(-text => 'Cancel', -width => 10, -command => sub {
		$self = thaw($freeze);
		$d->destroy;
	})->grid( -row => 0, -column => 1, -sticky => 'w');
				
		
	$f3->Button(-text => 'Preview', -width => 10, -command => sub {
		foreach my $k ( keys % { $self->{FAM} } ) {
			undef $self->{FAM}{$k}{$fam} if ! defined $def->{FAM}{$k};
		}								
		ProcessFamily($fam) or return undef;
		FindLoops($fam);				
		DoIt($fam);
		undef $flag;		
	})->grid( -row => 0, -column => 3, -sticky => 'w');
						
	
	### Radiobutton field for Selection of loop break modus
	#my $f2 = $d->Frame(-relief => 'groove', -borderwidth => 2)->pack( -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
	$f1->Radiobutton( -value => 0, -text => "No loop break", -variable => \$self->{FAM}{LOOP_BREAK_STATUS}{$fam},
	-command => sub { 
		$lb6->configure(-state=>'normal');
		$flag=1;
		for (my $i = 0; $i < $nr_loops; $i++) {						
			$self->{FAM}{BREAK_LOOP_OK}{$fam}{ $lb6->get($i) } = 0;
			$lb6->selectionClear($i);			
		}
		$lb6->configure(-state=>'disabled');
	}
	)->grid( -row => 0, -column => 1, -sticky => 'w');
	$f1->Radiobutton( -value => 2, -text => "Break all loops", -variable => \$self->{FAM}{LOOP_BREAK_STATUS}{$fam},
	-command => sub {
		$lb6->configure(-state=>'normal');
		$flag =1;
		for (my $i = 0; $i < $nr_loops; $i++) {	
			my ($p1, $p2) = split '==', $lb6->get($i);	
			$p1=$self->{FAM}{PID2PIDNEW}{$fam}{$p1};
			$p2=$self->{FAM}{PID2PIDNEW}{$fam}{$p2};
			my $p1p2 = join '==', nsort ($p1,$p2);
					
			$self->{FAM}{BREAK_LOOP_OK}{$fam}{$p1p2} = 1;
			$lb6->selectionSet($i);			
		}
		$lb6->configure(-state=>'disabled');
	}
	)->grid( -row => 2, -column => 1, -sticky => 'w');
	$f1->Radiobutton( -value => 3, -text => "Manually select loop break", -variable => \$self->{FAM}{LOOP_BREAK_STATUS}{$fam},
	-command => sub {$flag=1;$lb6->configure(-state=>'normal')}
	)->grid( -row => 3, -column => 1, -sticky => 'w');
			
	
	### choose PIDs for Loop break
	my $lab6 = $f2->Label(-text => 'Select loops for break', -width => 20)->pack(-side => 'top', -anchor => 'w');
	$lb6 = $f2->Scrolled('Listbox',
		-scrollbars => 'osoe', -selectmode => 'extended', -selectbackground => 	'red',
		-height => 14, -width => 25, -exportselection => 0
	)->pack(-side => 'top', -fill => 'both', -expand => 1);
	
		
	### Fill Listbox
	my @nodes = nsort keys % { $self->{FAM}{BREAK_LOOP_OK}{$fam} };
	foreach (@nodes) {
		my ($p1, $p2) = split '==', $_;
		$p1= $self->{FAM}{CASE_INFO}{$fam}{PID}{$p1}{'Case_Info_1'};
		$p2= $self->{FAM}{CASE_INFO}{$fam}{PID}{$p2}{'Case_Info_1'};
		$_ = join '==', nsort ($p1,$p2);
	}
		
	$lb6->insert('end', @nodes);		
	if ($self->{FAM}{LOOP_BREAK_STATUS}{$fam} == 3) {		
		for (my $i = 0; $i < $nr_loops; $i++) {
			my ($p1, $p2) = split '==', $lb6->get($i);
			$p1= $self->{FAM}{PID2PIDNEW}{$fam}{$p1};
			$p2= $self->{FAM}{PID2PIDNEW}{$fam}{$p2};
			$_ = join '==', nsort ($p1,$p2);
			if ($self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} == 1) {$lb6->selectionSet($i)}
			else {$lb6->selectionClear($i) }
		}
	}
	else { $lb6->configure(-state=>'disabled') }
		
	
	$lb6->bind('<ButtonRelease-1>' => sub {								
			my %save;
			$flag=1;
			foreach ($lb6->curselection()) { 
				my ($p1,$p2) = split '==', $lb6->get($_);
				$p1=$self->{FAM}{PID2PIDNEW}{$fam}{$p1};
				$p2=$self->{FAM}{PID2PIDNEW}{$fam}{$p2};
				my $p1p2 = join '==', nsort ($p1,$p2);
				$save{$p1p2} = 1 
			}
			foreach (keys % { $self->{FAM}{BREAK_LOOP_OK}{$fam} }) {
				if ($save{$_}) { $self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} = 1 }
				else { $self->{FAM}{BREAK_LOOP_OK}{$fam}{$_} = 0}
			}							
	});
	
	$d->Popup();	
	$d->idletasks;
	$d->iconimage($d->Photo(-format =>'gif',-data => GetIconData()));
	
	### to prevent manipulation from main wain window prior updated defaults 
	$d->grab	
}

# Configuratuion menu
#==================
sub Configuration {
#==================	
	### make copy of self for restoring data when cancel - action
	my $freeze = freeze($self);
	my %flag;
	
	if (! $self->{GLOB}{CURR_FAM}) { 
		ShowInfo("You have to load any pedigree first to change settings!", 'info'); return 
	}
	
	my $fam = $self->{GLOB}{CURR_FAM};
	
	my $opt = $mw->Toplevel(-title => "Configuration for family $self->{GLOB}{CURR_FAM}");						
	$opt->withdraw();
	
	my $f1 = $opt->Frame(-relief => 'groove', -borderwidth => 2)->pack( -side => 'top', -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
	my $f2 = $opt->Frame()->pack( -side => 'top', -padx => 5, -pady => 5,  -fill => 'x');
	
	### Buttons on bottom
	$f2->Button(-text => 'Ok', -width => 10, -command => sub {
		if ( $flag{X_SPACE} && $flag{X_SPACE} > 1) {
			BuildMatrix($fam); my $c=0; until (AlignMatrix($fam)) { $c++ ; last if $c > 120 }
		}
		ProcessHaplotypes();
		RedrawPed() ;
		$opt->destroy;
	})->grid( -row => 0, -column => 0, -sticky => 'w');
	
	$f2->Button(-text => 'Cancel', -width => 10, -command => sub {
		$self = thaw($freeze) if $self; 
		RedrawPed();
		$opt->destroy;
	})->grid( -row => 0, -column => 1, -sticky => 'w',-padx => 10);
				
		
	$f2->Button(-text => 'Preview', -width => 10, -command => sub {
		if ( $flag{X_SPACE} && $flag{X_SPACE} > 1  ) {
			BuildMatrix($fam);my $c=0; until (AlignMatrix($fam)) { $c++ ; last if $c > 120 }
		}
		
		ProcessHaplotypes();
		RedrawPed();
	})->grid( -row => 0, -column => 3, -sticky => 'w');

	### Notebook
	my $n = $f1->NoteBook(
		-background => '#28D0F0'
	)->pack(-expand => 1, -fill => 'both');

	my $p1 = $n->add( 'page1' , -label => 'Hap Style');
	my $p2 = $n->add( 'page2' , -label => 'Hap Show');
	my $p3 = $n->add( 'page3' , -label => 'Hap Color & Font');
	my $p4 = $n->add( 'page4' , -label => 'Hap Region');
	my $p5 = $n->add( 'page5' , -label => 'Ped Style');
	my $p6 = $n->add( 'page6' , -label => 'Ped Color');
	my $p7 = $n->add( 'page7' , -label => 'Ped & Case Info');
	

	###############################################################################
	### page1
	### place Scale Widgets
	my $p1_f1 = $p1->LabFrame(-label => 'Haplotype Style')->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'both', -expand =>1);
	foreach my $s (
		[ 'HAPLO_WIDTH'        , 'Bar width',                     0,0,   1, 50,    1  ],
		[ 'HAPLO_WIDTH_NI'     , 'Bar width uninformative',       1,0,   1, 50,    1  ],
		[ 'HAPLO_SPACE'        , 'Space between bars',            2,0,   1, 50,    1  ],
		[ 'HAPLO_LW'           , 'Line width',                    3,0, 0.1, 10,  0.1  ],
		[ 'LEGEND_SHIFT_LEFT'  , 'Legend distance left',          4,0,  20,500,    5  ],
		
		[ 'HAPLO_TEXT_LW'      , 'Allele distance',               0,1,   0,  5,  0.1  ],						
		[ 'MARKER_POS_SHIFT'   , 'Marker <-> position distance',  1,1,-500,500,    5  ],
		[ 'ALLELES_SHIFT'      , 'Allele position distance',      2,1,   0,100,    1  ],
		[ 'BBOX_WIDTH'         , 'Width of boundig boxes',        3,1,  10,100,    1  ],
		[ 'LEGEND_SHIFT_RIGHT' , 'Legend distance right',         4,1,  20,500,    5  ],
	) {
		$p1_f1->Scale(
			-label  => @$s[1], -variable => \$self->{FAM}{@$s[0]}{$fam},
			-from   => @$s[4], -to => @$s[5],-orient => 'horizontal',
			-length => 150, -width => 12, -resolution => @$s[6],
		)->grid( -row => @$s[2], -column => @$s[3], -sticky => 'ns');
		$p1_f1->gridColumnconfigure( @$s[2], -pad => 50);
	}

	###############################################################################
	### page2
	### place Checkbuttons
	my $p2_f1 = $p2->LabFrame(-label => 'Haplotype & Map')->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'both', -expand =>1);
	foreach my $s (
		[ 'SHOW_HAPLO_TEXT'	      , 'Show alleles',                            0,0  ],
		[ 'SHOW_HAPLO_BAR'	      , 'Show bars',                               1,0  ],
		[ 'SHOW_POSITION'         , 'Show marker positions',                   2,0  ],
		[ 'SHOW_MARKER'           , 'Show marker names',                       3,0  ],
		[ 'SHOW_HAPLO_BBOX'       , 'Show haplotypes bounding box',            4,0  ],
		[ 'SHOW_INNER_SYBOL_TEXT' , 'Show text inside symbols',                5,0  ],
		[ 'ALIGN_LEGEND',         , 'Justify map legend',                      6,0  ],
		[ 'SHOW_COLORED_TEXT',    , 'Show alleles like bar colours',           7,0  ],
		[ 'FILL_HAPLO'		        , 'Fill out bars',                           0,1  ],
		[ 'SHOW_HAPLO_NI_0'       , 'Show completly lost Haplotypes',          1,1  ],
		[ 'SHOW_HAPLO_NI_1'       , 'Show other lost genotypes',               2,1  ],
		[ 'SHOW_HAPLO_NI_2'       , 'Show user defined non-informative',       3,1  ],
		[ 'SHOW_HAPLO_NI_3'       , 'Show other non-informative',              4,1  ],
		[ 'HAPLO_SEP_BL'          , 'Draw each allele as separate bar',        5,1  ],
		[ 'SHOW_LEGEND_LEFT'      , 'Show legend left',                        6,1  ],
		[ 'SHOW_LEGEND_RIGHT'     , 'Show legend right',                       7,1  ],
	) {
		$p2_f1->Checkbutton( -text => @$s[1], -variable => \$self->{FAM}{@$s[0]}{$fam},
		)->grid( -row => @$s[2], -column => @$s[3], -sticky => 'w');
		$p2_f1->gridColumnconfigure( @$s[2], -pad => 30);
	}

	###############################################################################
	### page3
	### Fonts + Colors
	my $p3_f1 = $p3->LabFrame(-label => 'Haplotype Color & Font')->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'both', -expand =>1);
	
	my $hap_f = $p3_f1->Frame->grid(-row => 0, -column => 0, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $hap_l = $hap_f->Label(-width => 3, -bg => $self->{FAM}{FONT_HAPLO}{$fam}{COLOR})->pack(-side => 'left', -padx => 10);
	my $hap_b; $hap_b = $hap_f->Button( -text => 'Haplotype Font', -width => 20, -command => sub {
		ChooseFont($opt, $fam,'FONT_HAPLO', $hap_l);
	})->pack(-side => 'left');
	my $inf_f = $p3_f1->Frame->grid(-row => 1, -column => 0, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $inf_l = $inf_f->Label(-width => 3, -bg => $self->{FAM}{FONT1}{$fam}{COLOR})->pack(-side => 'left', -padx => 10);
	my $inf_b; $inf_b = $inf_f->Button( -text => 'Symbol information Font', -width => 20,-command => sub {
		ChooseFont($opt, $fam,'FONT1', $inf_l)
	})->pack(-side => 'left');
	my $head_f = $p3_f1->Frame->grid(-row => 2, -column => 0, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $head_l = $head_f->Label(-width => 3, -bg => $self->{FAM}{FONT_HEAD}{$fam}{COLOR})->pack(-side => 'left', -padx => 10);
	my $head_b; $head_b = $head_f->Button( -text => 'Title Font', -width => 20, -command => sub {
		ChooseFont($opt, $fam,'FONT_HEAD', $head_l)
	})->pack(-side => 'left');


	### Farbe fuer HAPLO_UNKNOWN
	my $fc2 = $p3_f1->Frame->grid(-row => 3, -column => 0, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $lb2 = $fc2->Label(-width => 3, -bg => $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam})->pack(-side => 'left', -padx => 10);
	my $ub; $ub = $fc2->Button(
		-text => 'Phase unknown color',
		-width => 20, -height => 1,-command => sub {
			my $col = $mw->chooseColor() or return;
			$self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam} = $col;
			$lb2->configure(-bg => $col)
	})->pack(-side => 'left');

	### Farbe f�r ALLE HAPLOTYPEN
	my $fc5 = $p3_f1->Frame->grid(-row => 4, -column => 0, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $lb5 = $fc5->Label(-width => 3, -bg => $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam})->pack(-side => 'left', -padx => 10);
	$fc5->Button(-text => 'Color of all haplotypes ',-width => 20, -height => 1,-command => sub {
		my $col_new = $mw->chooseColor() or return;
		foreach my $p (keys %{$self->{FAM}{FOUNDER}{$fam}}) {
			next unless $self->{FAM}{HAPLO}{$fam}{PID}{$p};
			foreach my $mp ( 'M', 'P' ) {
				next if $self->{FAM}{HAPLO}{$fam}{PID}{$p}{$mp}{SAVE} ;
				foreach my $r (@ { $self->{FAM}{HAPLO}{$fam}{PID}{$p}{$mp}{BAR} }) {@$r[1] = $col_new }
			}
		}
		$lb5->configure(-bg => $col_new);
		$opt->focusForce;
		ProcessHaplotypes();
	})->pack(-side => 'left');


	my $fc3 = $p3_f1->Frame->grid(-row => 1, -column => 2, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $lb3 = $fc3->Label(-width => 3)->pack(-side => 'left', -padx => 10);
	my ($pb, $pid, $pid_old);
	$pb = $fc3->Button(
		-text => 'Color of paternal Haplotype',
		-width => 25, -height => 1,-command => sub {					
			if ($pid && $self->{FAM}{HAPLO}{$fam}{PID}{$pid} && $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{BAR}[0]) {
				my $col_new = $n->chooseColor() or return;
				my $col_old = $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{BAR}[0][1] or return;
				foreach my $mp ( 'M', 'P' ) {
					foreach my $r (@ { $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{$mp}{BAR} }) {
						@$r[1] = $col_new if $col_old eq @$r[1];
					}
				}
				$lb3->configure(-bg => $col_new);
				$opt->focusForce;	
			}
	})->pack(-side => 'left');

	my $fc4 = $p3_f1->Frame->grid(-row => 2, -column => 2, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $lb4 = $fc4->Label(-width => 3)->pack(-side => 'left', -padx => 10);
	my $mb; $mb = $fc4->Button(
		-text => 'Color of maternal Haplotype',
		-width => 25, -height => 1,-command => sub {
			#print "PID:$pid\n";
			if ($pid && $self->{FAM}{HAPLO}{$fam}{PID}{$pid} && $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{BAR}[0]) {
				my $col_new = $n->chooseColor() or return;
				my $col_old = $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{BAR}[0][1] or return;			
				foreach my $mp ( 'M', 'P' ) {
					foreach my $r (@ { $self->{FAM}{HAPLO}{$fam}{PID}{$pid}{$mp}{BAR} }) {
						@$r[1] = $col_new if $col_old eq @$r[1];
					}
				}
				$lb4->configure(-bg => $col_new);
				$opt->focusForce;
			}
	})->pack(-side => 'left');


	my $cbs1 = $p3_f1->Checkbutton( -text => 'Anchor paternal haplotype',
	)->grid( -row => 3, -column => 2, -sticky => 'w');
	my $cbs2 = $p3_f1->Checkbutton( -text => 'Anchor maternal haplotype',
	)->grid( -row => 4, -column => 2, -sticky => 'w');

	my $cbs3 = $p3_f1->Checkbutton( -text => 'Hide paternal haplotype',
	)->grid( -row => 5, -column => 2, -sticky => 'w');
	my $cbs4 = $p3_f1->Checkbutton( -text => 'Hide maternal haplotype',
	)->grid( -row => 6, -column => 2, -sticky => 'w');


	### personenbezogene Einstellungen
	@_ = nsort keys %{$self->{FAM}{FOUNDER}{$fam}};
	foreach (@_) { $_ = $self->{FAM}{CASE_INFO}{$fam}{PID}{$_}{'Case_Info_1'} }
	my $be5 = $p3_f1->BrowseEntry(
		-label => '        Founder:', -variable => \$pid_old,
		-choices => [ @_  ], -width => 15,	-state => 'readonly',
		-browsecmd => sub {
			$pid = $self->{FAM}{PID2PIDNEW}{$fam}{$pid_old};
			foreach (@{$self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{BAR}}) {
				if (@$_[1] ne $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam}) { $lb3->configure(-bg => @$_[1]); last }
			}
			foreach (@{$self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{BAR}}) {
				if (@$_[1] ne $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam}) { $lb4->configure(-bg => @$_[1]); last }
			}
			if ($self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{SAVE}) {$_ = 'disabled'}
			else { $_ = 'normal' } $pb->configure(-state => $_);
			if ($self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{SAVE}) {$_ = 'disabled'}
			else { $_ = 'normal' } $mb->configure(-state => $_);
			$cbs1->configure(
				-variable =>  \$self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{SAVE},
				-command => sub {
					if ($self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{SAVE}) {
						$pb->configure(-state => 'disabled')
					} else { $pb->configure(-state => 'normal')	}
			});
			$cbs2->configure(
				-variable =>  \$self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{SAVE},
				-command => sub {
					if ($self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{SAVE}) {
						$mb->configure(-state => 'disabled')
					} else { $mb->configure(-state => 'normal')	}
			});
			$cbs3->configure(-variable =>  \$self->{FAM}{HAPLO}{$fam}{PID}{$pid}{P}{HIDE});
			$cbs4->configure(-variable =>  \$self->{FAM}{HAPLO}{$fam}{PID}{$pid}{M}{HIDE});
			$opt->focusForce;

	})->grid(-row => 0, -column => 2, -sticky => 'w');
	for ( 0..8 ) { $p3_f1->gridRowconfigure( $_, -pad => 10) }
	$p3_f1->gridColumnconfigure( 0, -pad => 40) ;

	###############################################################################
	### page4
	### Listbox Markerauswahl +  Bounding Box
	### Markerauswahl
	my $p4_f1 = $p4->LabFrame(-label => 'Haplotype region')->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'both', -expand =>1);
	my $f5 = $p4_f1->Frame->grid(-row => 1, -column => 0, -sticky => 'w');
	my $lab5 = $f5->Label(-text => 'Marker Selection', -width => 20)->pack(-side => 'top', -anchor => 'w');
	my $lb = $f5->Scrolled('Listbox',
		-scrollbars => 'osoe', -selectmode => 'extended', -selectbackground => 	'red',
		-height => 14, -width => 25, -exportselection => 0,
	)->pack(-side => 'top', -fill => 'both', -expand => 1);
	$p4->gridColumnconfigure( 0, -pad => 10);

	if ($self->{FAM}{MAP}{$fam}{MARKER}) {
		@_ = @{$self->{FAM}{MAP}{$fam}{MARKER}};
		for (my $i = 0; $i < scalar @_; $i++) {
			my $j = ''; unless ( defined $self->{FAM}{MAP}{$fam}{POS}[$i] ) {
				$j = sprintf ("%03.0f - ", $i+1);
			} else {
				$j = sprintf ("%6.2f - ", $self->{FAM}{MAP}{$fam}{POS}[$i]);
			}

			$lb->insert('end', "$j$_[$i]");
			$lb->selectionSet($i) if $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
		}
	}

	$lb->bind('<ButtonRelease-1>' => sub {
		if ($self->{FAM}{MAP}{$fam}{MARKER}) {
			my %h; foreach ($lb->curselection()) { $h{$_} = 1 }
			for (my $i = 0; $i < scalar @{$self->{FAM}{MAP}{$fam}{MARKER}}; $i++) {
				if ($h{$i}) { $self->{FAM}{HAPLO}{$fam}{DRAW}[$i] = 1 }
				else { $self->{FAM}{HAPLO}{$fam}{DRAW}[$i] = 0 }
			}
		}
	});

	$opt->bind('<Control-Key-a>' => sub {
		if ($self->{FAM}{MAP}{$fam}{MARKER}) {
			@_ = @{$self->{FAM}{MAP}{$fam}{MARKER}};
			if (@_) {
				for (my $i = 0; $i < scalar @_; $i++) {
					$lb->selectionSet($i) ;
					$self->{FAM}{HAPLO}{$fam}{DRAW}[$i] = 1;
				}
			}
		}
	});

	### Boundig Box
	@_ = nsort keys %{$self->{FAM}{PID}{$fam}};
	foreach (@_) { $_ = $self->{FAM}{CASE_INFO}{$fam}{PID}{$_}{'Case_Info_1'} }
	my ($person, $lb6, $sid_new);
	my $be6 = $p4_f1->BrowseEntry(
		-label => 'Sample', -variable => \$person,
		-choices => [ @_  ], -width => 12,	-state => 'readonly',
		-browsecmd => sub {
			$sid_new = $self->{FAM}{PID2PIDNEW}{$fam}{$person};
			if ($self->{FAM}{HAPLO}{$fam}{PID}{$sid_new}{P}{TEXT}) {
				my $h = $self->{FAM}{HAPLO}{$fam}{PID}{$sid_new};
				@_ = @{$self->{FAM}{MAP}{$fam}{MARKER}};
				$lb6->delete(0,'end');
				for (my $i = 0; $i < scalar @_; $i++) {
					my $j = ''; if ( @{ $self->{FAM}{MAP}{$fam}{POS} } ) {
						$j = sprintf ("%6.2f - ", $self->{FAM}{MAP}{$fam}{POS}[$i]);
					}
					my $alstr = "($h->{P}{TEXT}[$i]\\$h->{M}{TEXT}[$i])";
					$lb6->insert('end', "$j$_[$i] $alstr");
					$lb6->selectionSet($i) if $h->{BOX}[$i];
				}
			}
	})->grid(-row => 0, -column => 1, -sticky => 's');
	$p4->gridRowconfigure( 1, -pad => 10);

	my $f6 = $p4_f1->Frame->grid(-row => 1, -column => 1, -rowspan => 7, -sticky => 'w');
	my $lab6 = $f6->Label(-text => 'Boundig Box Selection', -width => 20)->pack(-side => 'top', -anchor => 'w');
	$lb6 = $f6->Scrolled('Listbox',
		-scrollbars => 'osoe', -selectmode => 'extended', -selectbackground => 	'red',
		-height => 14, -width => 25, -exportselection => 0,
	)->pack(-side => 'top', -fill => 'both', -expand => 1);
	$p4->gridColumnconfigure( 1, -pad => 10);

	$lb6->bind('<ButtonRelease-1>' => sub {
		if ($self->{FAM}{MAP}{$fam}{MARKER}) {
			my %h; foreach ($lb6->curselection()) { $h{$_} = 1 }
			for (my $i = 0; $i < scalar @{$self->{FAM}{MAP}{$fam}{MARKER}}; $i++) {
				if ($h{$i}) { $self->{FAM}{HAPLO}{$fam}{PID}{$sid_new}{BOX}[$i] = 1 }
				else { $self->{FAM}{HAPLO}{$fam}{PID}{$sid_new}{BOX}[$i] = 0 }
			}
		}
	});

	###############################################################################
	### page5
	### Lines Option Schieberegler
	my $p5_f1 = $p5->LabFrame(-label => 'Pedigree style')->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'both', -expand =>1);
	foreach my $s (
		[ 'CROSS_FAKTOR1',     'Cross factor',                0,0,   0.1,  5,  0.1  ],
		[ 'ALIVE_SPACE',       'Deceased line length',        1,0,     1, 20,    1  ],
		[ 'GITTER_X',          'Grid X space',                2,0,     5, 50,    1  ],
		[ 'GITTER_Y',          'Grid Y space',                3,0,     5, 50,    1  ],
		[ 'CONSANG_DIST',      'Consanguinity line distance', 0,1,     1, 10,    1  ],
		[ 'LINE_SIBS_Y',       'Intersib Y distance',         1,1,    15, 50,    1  ],
		[ 'SYMBOL_SIZE',       'Symbol size',                 2,1,     5, 50,    1  ],
		[ 'SYMBOL_LINE_WIDTH', 'Symbol outer line width',     3,1,   0.1,  5,  0.1  ],
		[ 'LINE_WIDTH',        'Line width',                  0,2,   0.1,  5,  0.1  ],
		[ 'X_SPACE',           'Inter symbol distance',       1,2,     1, 40,    1  ],
		[ 'Y_SPACE_DEFAULT',   'Inter generation distance',   2,2,     3, 40,    1  ],
		[ 'Y_SPACE_EXTRA',     'Haplo extra space',           3,2,     2, 50,    1  ],
	) {
		$p5_f1->Scale(
			-label  => @$s[1], -variable => \$self->{FAM}{@$s[0]}{$fam},
			-from   => @$s[4], -to => @$s[5],-orient => 'horizontal',
			-length => 130, -width => 12, -resolution => @$s[6],-command => sub {
				### reason: changing X_SPACE must follow building the Matrix and Aligning new.
				### As invoking notepad page for the first time activate the callback like moving slider too, 
				### a counter is used here
				$flag{@$s[0]}++ if @$s[0] eq 'X_SPACE'					
			}
		)->grid( -row => @$s[2], -column => @$s[3], -sticky => 'w');
		$p5_f1->gridColumnconfigure( @$s[2], -pad => 20);
	}

	###############################################################################
	### page6
	### Lines Option Farben
	my $p6_f1 = $p6->LabFrame(-label => 'Color')->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'both', -expand =>1);
	
	my %c = (
		AFF_COLOR => {
			0 => '#0 unknown affected',
			1 => '#1 not affected', 
			2 => '#2 affected', 
			3 => '#3 affected', 
			4 => '#4 affected', 
			5 => '#5 affected', 
			6 => '#6 affected', 
			7 => '#7 affected', 
			8 => '#8 affected', 
			9 => '#9 affected'  
		},
		LC => {
			0 => ['LINE_COLOR', 'Line color' ],
			1 => ['SYMBOL_LINE_COLOR', 'Symbol line color'],  
			2 => ['ARROW_COLOR', 'Proband arrow color']
		}
	);
	
	for my $nr( sort { $a <=> $b } keys % { $c{AFF_COLOR} } ) {		
		my $f = $p6_f1->Frame->grid(-row => $nr, -column => 0, -sticky => 'w');
		my $lb = $f->Label(-width => 3, -bg => $self->{FAM}{AFF_COLOR}{$fam}{$nr})->pack(-side => 'left', -padx => 10);
		my $cb; $cb = $f->Button(
		-text => $c{AFF_COLOR}{$nr},
		-width => 20, -height => 1,-command => sub {
			my $NewCol = $mw->chooseColor() or return;
			$self->{FAM}{AFF_COLOR}{$fam}{$nr} = $NewCol;
			$lb->configure(-bg => $NewCol);
			$opt->focusForce;
		})->pack(-side => 'left');		
	}
	
	for my $nr( sort { $a <=> $b } keys % { $c{LC} } ) {		
		my $f = $p6_f1->Frame->grid(-row => $nr, -column => 1, -sticky => 'w'); 
		my $lb = $f->Label(-width => 3, -bg => $self->{FAM}{$c{LC}{$nr}[0]}{$fam})->pack(-side => 'left', -padx => 10);
		my $cb; $cb = $f->Button(
		-text => $c{LC}{$nr}[1],
		-width => 20, -height => 1,-command => sub {
			my $NewCol = $mw->chooseColor() or return;
			$self->{FAM}{$c{LC}{$nr}[0]}{$fam} = $NewCol;
			$lb->configure(-bg => $NewCol);
			$opt->focusForce;
		})->pack(-side => 'left');		
		
		if ($nr==1) {
			$f->Checkbutton( -text => "Set for affected", -variable => \$self->{FAM}{SYMBOL_LINE_COLOR_SET}{$fam},
			)->pack(-side => 'left');					
		}		
	}
	
	my $f = $p6_f1->Frame->grid(-row => 4, -column => 1, -sticky => 'w');
	my $lab = $f->Label(-width => 3, -bg => $self->{GLOB}{BACKGROUND})->pack(-side => 'left', -padx => 10);
	my $cb7; $cb7 = $f->Button(
		-text => 'Background color',
		-width => 20, -height => 1,-command => sub {
			my $NewCol = $mw->chooseColor() or return;
			$self->{GLOB}{BACKGROUND} = $NewCol;
			$lab->configure(-bg => $NewCol);
			$canvas->configure(-bg => $self->{GLOB}{BACKGROUND});
			$opt->focusForce;
	})->pack(-side => 'left');
	

	$f->Checkbutton( -text => "Export background", -variable => \$self->{FAM}{EXPORT_BACKGROUND}{$fam},
	)->pack(-side => 'left');					

  
	for ( 0..9 ) { $p6_f1->gridRowconfigure( $_, -pad => 2) }

	###############################################################################
	### page7
	### case info
	
	my $p7_f1 = $p7->LabFrame(-label => 'Title')->pack(-side => 'top', -padx => 5, -pady => 5,  -fill => 'x');
	my $p7_f3 = $p7->LabFrame(-label => 'Case Info')->pack( -side => 'top', -padx => 5, -pady => 5,  -fill => 'x'); 
	
	$p7_f1->Checkbutton( -text => "Show", -variable => \$self->{FAM}{SHOW_HEAD}{$fam},
	)->grid( -row => 0, -column => 0, -sticky => 'e',-pady => 10);
	
	$p7_f1->Entry(-textvariable => \$self->{FAM}{TITLE}{$fam}, -width => 40,
	)->grid(-row => 0, -column => 1, -sticky => 'w');

	$p7_f1->BrowseEntry(
		-label => 'Font size: ',-variable => \$self->{FAM}{FONT_HEAD}{$fam}{SIZE}, -command => sub { },
		-width => 5,-choices =>	[ 5 .. 20, 22, 24, 26, 28, 36, 48, 72 ],-state => 'readonly'
	)->grid(-row => 0, -column => 2, -sticky => 'w');	
			
	foreach my $col ( 1 .. 5 ) {			
		$p7_f3->BrowseEntry(
			-label => 'Case  ' . $col,-labelPack => [ -side => 'left', -anchor => 'w' ],						
			-variable => \$self->{FAM}{CASE_INFO}{$fam}{COL_TO_NAME}{$col}, -state => 'readonly',
			-choices => [  nsort keys  % { $self->{FAM}{CASE_INFO}{$fam}{COL_NAMES} } ]
		)->grid(-row => $col, -column => 0,  -sticky => 'w');
		$p7_f3->Checkbutton( -text => 'Show',-variable => \$self->{FAM}{CASE_INFO_SHOW}{$fam}{$col}
		)->grid( -row => $col, -column => 1, -sticky => 's');
	}			
	$p7_f3->Label->grid(-row => 6);
	
	$opt->Popup();	
	$opt->idletasks;
	$opt->iconimage($opt->Photo(-format =>'gif',-data => GetIconData()));
	
	### to prevent manipulation from main wain window prior updated defaults 
	$opt->grab;
}    	


#===============
sub ChooseFont {
#===============	
	my ($opt,$fam,$k,$lab) = @_;
	my ($a, $c, $cb1);
	my $fo = $self->{FAM}{$k}{$fam};
	$opt->grabRelease;
	my $tl = $opt->Toplevel();
	$tl->title('Font');
	$tl->grab();

	my $f1 = $tl->Frame(-relief => 'groove', -borderwidth => 2)->pack( -side => 'top', -padx => 5, -pady => 5, -expand => 1, -fill => 'both');
	my $f2 = $tl->Frame()->pack( -side => 'top', -padx => 5, -pady => 5,  -fill => 'x');
		
	
	### Font Familie
	my $fe1 = $f1->Frame->grid(-row => 0, -column => 1, -sticky => 'w');
	my $lab1 = $fe1->Label(-text => 'Font:', -width => 6)->pack(-side => 'left', -anchor => 'w');
	my $be1 = $fe1->BrowseEntry(
		-variable => \$fo->{FAMILY}, -state => 'readonly',
		-choices => [ nsort $mw->fontFamilies, 'Lucida' ],
		-command => sub { $cb1->configure(-font => [ $fo->{FAMILY}, 8, $fo->{WEIGHT}, $fo->{SLANT} ]) }
	)->pack(-side => 'left');

    ### Font Groesse
    my $fe2 = $f1->Frame->grid(-row => 1, -column => 1, -sticky => 'w');
    my $lab2 = $fe2->Label(-text => 'Size:', -width => 6)->pack(-side => 'left', -anchor => 'w');
    my $be2 = $fe2->BrowseEntry(
		-variable => \$fo->{SIZE}, -state => 'readonly',
		-choices => [ 5 .. 20, 22, 24, 26, 28, 36, 48, 72 ],
	)->pack(-side => 'left');

	### Font Weight
	my $fe3 = $f1->Frame->grid(-row => 2, -column => 1, -sticky => 'w');
    my $lab3 = $fe3->Label(-text => 'Weight:', -width => 6)->pack(-side => 'left', -anchor => 'w');
    my $be3 = $fe3->BrowseEntry(
		-variable => \$fo->{WEIGHT},-choices => [ 'bold', 'normal' ], -state => 'readonly',
		-command => sub { $cb1->configure(-font => [ $fo->{FAMILY}, 10, $fo->{WEIGHT}, $fo->{SLANT} ]) }
	)->pack(-side => 'left');

	### Font Style
	my $fe4 = $f1->Frame->grid(-row => 3, -column => 1, -sticky => 'w');
    my $lab4 = $fe4->Label(-text => 'Slant:', -width => 6)->pack(-side => 'left', -anchor => 'w');
    my $be4 = $fe4->BrowseEntry(
		-variable => \$fo->{SLANT},  -state => 'readonly',-choices => [ 'italic', 'roman',  ]	,
		-command => sub { $cb1->configure(-font => [ $fo->{FAMILY}, 10, $fo->{WEIGHT}, $fo->{SLANT} ]) }
	)->pack(-side => 'left');

	### Font Farbe
	my $fc1 = $f1->Frame->grid(-row => 5, -column => 1, -sticky => 'w');                                                                                                                                                                                 	### Font Farbe
	my $lb1 = $fc1->Label(-width => 3, -bg => $fo->{COLOR})->pack(-side => 'left', -padx => 10);
	$cb1 = $fc1->Button(
		-text => 'Choose Font Color',
		-font => [ $fo->{FAMILY}, 10, $fo->{WEIGHT}, $fo->{SLANT} ],
		-width => 24, -height => 1,-command => sub {
			my $NewCol = $mw->chooseColor() or return;
			$fo->{COLOR} = $NewCol;
			$lb1->configure(-bg => $NewCol);
			$lab->configure(-bg => $fo->{COLOR}) if $lab;
			$tl->focusForce;
	})->pack();

	$f1->gridRowconfigure( 5, -pad => 30);

	$f2->Button(-text => 'Ok', -width => 10, -command => sub {
		$tl->destroy(); 
		$opt->focusForce;
		$opt->grab;
	})->grid( -row => 0, -column => 0, -sticky => 'w');
	
	$tl->withdraw();
	$tl->Popup();	
	$tl->idletasks;
	$tl->iconimage($opt->Photo(-format =>'gif',-data => GetIconData()));
	
}

# Export all pedigrees in given format
#================
sub BatchExport {
#==============
	my $suffix = shift @_ or return undef;
	ShowInfo("Please select working directory and a basic file name without suffix.\nGraphic outputs will be extended by pedigree identifiers.\n\n");
	my $file = $mw->getSaveFile(-initialfile => 'pedigree') or return;	
	my $curr_fam = $self->{GLOB}{CURR_FAM};
	foreach my $fam (nsort keys % { $self->{FAM}{PED_ORG} }) {
		my $file = File::Spec->catfile( dirname($file), basename($file) . '_' . $fam . '.' . $suffix);	
		if (! $self->{FAM}{MATRIX}{$fam}) { 
			$self->{GLOB}{CURR_FAM} = $fam;
			DoIt() 
		}
		DrawOrExportCanvas(-modus => $suffix, -fam => $fam, -file => $file);
	}	
	$self->{GLOB}{CURR_FAM} = $curr_fam if $curr_fam;
}


# adapt canvas scroll region and center/fit views
#===============
sub AdjustView {
#===============	
	shift @_ if ref $_[0];
	my %arg = @_;
	my $fam = $self->{GLOB}{CURR_FAM} or return;
	my $c = $canvas;
	my $s = $param->{SHOW_GRID};
	my $z = $self->{FAM}{ZOOM}{$fam};
	return if $batch;
	
	
	$param->{SHOW_GRID} = 0;
	ShowGrid();
	
	my @bx = $c->bbox('all');
	
	unless (@bx) {
		$param->{SHOW_GRID} = $s;
		ShowGrid();				
		return;
	}
	
	### scrollbar size ( left and right point of slider position, is between 0 and 1)
	my @xv = $c->xview;
	my @yv = $c->yview;
	
	my @sc = $c->Subwidget('canvas')->cget(-scrollregion);

	### size of bounding box
	my $xbd = $bx[2]-$bx[0];
	my $ybd = $bx[3]-$bx[1];
			
	### relative size of sliding window (size of slider --> if 1 then sliding window = whole canvas)
	my $xvd = $xv[1]-$xv[0];
	my $yvd = $yv[1]-$yv[0];

	### size of canvas scrollable region
	my $xsd = $sc[2]-$sc[0];
	my $ysd = $sc[3]-$sc[1];
	
	### sliding window size
	my $wx = $xsd*$xvd;
	my $wy = $ysd*$yvd;
	
	### scroll buffer
	my ($scrx, $scry) = ($xbd, $ybd);
	if ($scrx < (1.5*$wx)) { $scrx = 1.5*$wx }
	if ($scry < (1.5*$wy)) { $scry = 1.5*$wy }
	
	### just shift to middle point of the drawing wihout zoom
	if (! $arg{-fit}) {
		$c->configure(-scrollregion => [ $bx[0]-$scrx, $bx[1]-$scry, $bx[2]+$scrx, $bx[3]+$scry ]);
		
		my @xv = $c->xview;
		my @yv = $c->yview;
		
		$c->xviewMoveto(0.5-(($xv[1]-$xv[0])*0.5));
		$c->yviewMoveto(0.5-(($yv[1]-$yv[0])*0.5));		
		
	}
	### Center and fit the view
	elsif ( $arg{-fit} eq 'center') {					
		
		### adapt zoom factor to bounding box + 10% border
		if ($ybd && $wy) {
			if  ($xbd/$ybd > $wx/$wy) {
				$self->{FAM}{ZOOM}{$fam} *= $wx/$xbd*0.9} else { $self->{FAM}{ZOOM}{$fam} *= $wy/$ybd*0.9  
			}
		}
		
		RedrawPed();
		
		### adapt canvas scroll region to fit the drawing bounding box and center scrollbars
		my @bx = $canvas->bbox('all');
		
		my $xbd = $bx[2]-$bx[0];
		my $ybd = $bx[3]-$bx[1];
		
		my ($scrx, $scry) = ($xbd, $ybd);
		if ($scrx < (1.5*$wx)) { $scrx = 1.5*$wx }
		if ($scry < (1.5*$wy)) { $scry = 1.5*$wy }
	
		$c->configure(-scrollregion => [ $bx[0]-$scrx, $bx[1]-$scry, $bx[2]+$scrx, $bx[3]+$scry ]);
						
		my @xv = $c->xview;
		my @yv = $c->yview;
						
		$c->xviewMoveto(0.5-(($xv[1]-$xv[0])*0.5));
		$c->yviewMoveto(0.5-(($yv[1]-$yv[0])*0.5));
		
	}
	### Zooming to cursor position
	elsif ($arg{-fit} eq 'to_button') {				
		
		### last stored canvas position in respect of corresponding cursor position
		my $x = $self->{GLOB}{X_CANVAS};
		my $y = $self->{GLOB}{Y_CANVAS};				
		
		### center canvas scrollregion to that coordinates				
		my @sc = ( $x-$scrx, $y-$scry, $x+$scrx, $y+$scry );
		$c->configure(-scrollregion => \@sc);
		
		my @xv = $c->xview;
		my @yv = $c->yview;
						
		my $xvd = $xv[1]-$xv[0];
		my $yvd = $yv[1]-$yv[0];
		  	
		my $xsd = $sc[2]-$sc[0];
		my $ysd = $sc[3]-$sc[1];
					
		my $wx = $xsd*$xvd;
		my $wy = $ysd*$yvd;
						
		my $x_diff = $x-$c->canvasx($self->{GLOB}{X_SCREEN});		
		my $y_diff = $y-$c->canvasy($self->{GLOB}{Y_SCREEN});
		
		my $prop_x = 1-$xvd;
		my $prop_y = 1-$yvd;
		
		my $moveto_x = $xv[0] + ( ($prop_x*$x_diff)/($xsd-$wx) );
		my $moveto_y = $yv[0] + ( ($prop_y*$y_diff)/($ysd-$wy) );
		
		$c->xviewMoveto($moveto_x);	
		$c->yviewMoveto($moveto_y);						
	}
	
	$param->{SHOW_GRID} = $s;
	ShowGrid();
	
	### Store canvas and scrollbar positions
	StoreDrawPositions()
		
}

#=============
sub ShowGrid {
#=============	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	return unless $fam;
	my $z = $self->{FAM}{ZOOM}{$fam};
	if ($param->{SHOW_GRID}) {
		$canvas->createGrid( 0,0, $self->{FAM}{GITTER_X}{$fam}*$z,$self->{FAM}{GITTER_Y}{$fam}*$z,-lines => 1, -fill => 'grey90', -tags => 'GRID');
		$canvas->Subwidget('canvas')->lower('GRID');
	} else {
		$canvas->delete('GRID')
	}
}


#=======================
sub DrawOrExportCanvas {
#=======================
	my %arg = @_;
	my $fam = $arg{-fam} || $self->{GLOB}{CURR_FAM};
	my $z = $self->{FAM}{ZOOM}{$fam};
	my $l = $self->{FAM}{LINE_WIDTH}{$fam};
	my $lnc = $self->{FAM}{LINE_COLOR}{$fam};
	my $de = $self->{FAM}{DRAW_ELEMENTS}{$fam}{CANVAS};
	my $d = $self->{FAM}{LINES}{$fam};
	my $f1 = $self->{FAM}{FONT1}{$fam};
	### draw pedigree in a Tk widget 
	if (! $arg{-modus}) {
		
		### clear canvas and rebuild grid
		$canvas->delete('all');
		ShowGrid();
		
		### Lines betwwen symbols			
		foreach my $parent_node (keys %{$d->{COUPLE}}) {
			foreach my $ln ( @{$d->{COUPLE}{$parent_node}} ) {					
				$canvas->createLine(@$ln, -width => $l*$z,-fill => $lnc)						
			}
		}			
		foreach my $id (keys %{$d->{SIB}}) {
			foreach my $ln ( @{$d->{SIB}{$id}} ) {					
				$canvas->createLine(@$ln, -width => $l*$z,-fill => $lnc)						
			}
		}			
		foreach my $id (keys %{$d->{COUPLE_SIB}}) {
			foreach my $ln ( @{$d->{COUPLE_SIB}{$id}} ) {					
				$canvas->createLine(@$ln, -width => $l*$z,-fill => $lnc)						
			}
		}
		foreach my $id (keys %{$d->{TWIN_LINES}}) {
			foreach my $ln ( @{$d->{TWIN_LINES}{$id}} ) {					
				$canvas->createLine(@$ln, -width => $l*$z,-fill => $lnc)						
			}
		}
		
		### Drawing male SYMBOL Elements
		foreach my $r (@ { $de->{SYM_MALE} }) { $canvas->createRectangle(@$r) }		
		### Drawing female SYMBOL Elements
		foreach my $r (@ { $de->{SYM_FEMALE} }) { $canvas->createOval(@$r) }		
		### Drawing stillbirth SYMBOL Elements
		foreach my $r (@ { $de->{SYM_STILLBIRTH} }) { $canvas->createPolygon(@$r) }		
		### Drawing unknown SYMBOL Elements
		foreach my $r (@ { $de->{SYM_UNKNOWN} }) { $canvas->createPolygon(@$r) }					
		#### Drawing  Text elements
		foreach my $e (qw/  INNER_SYMBOL_TEXT CASE_INFO TITLE PROBAND_TEXT MARK_TEXT SAB_GENDER/ ) {foreach my $r (@ { $de->{$e} }) { $canvas->createText(@$r)}}			
		### Drawing live status line
		foreach my $r (@ { $de->{LIVE_LINE} }) { $canvas->createLine(@$r) }		
		### Haplotype Bar not informative
		foreach my $r (@ { $de->{HAP_BAR_NI} }) { $canvas->createRectangle(@$r) }	
		### Haplotype Bar
		foreach my $r (@ { $de->{HAP_BAR} }) { $canvas->createRectangle(@$r) }							
		### Haplotype Bounding Box
		foreach my $r (@ { $de->{HAP_BOX} }) { $canvas->createRectangle(@$r) }							
		### Haplotype Text
		foreach my $e (qw /HAP_TEXT MAP_MARKER_LEFT MAP_MARKER_RIGHT MAP_POS_LEFT MAP_POS_RIGHT /) {
			foreach my $r (@ { $de->{$e} }) { $canvas->createText(@$r) }					
		}	
		### Arrows
		foreach my $r (@ { $de->{ARROWS} }) { $canvas->createLine(@$r) }				
		### Adopted lines
		foreach my $r (@ { $de->{IS_ADOPTED} }) { $canvas->createLine(@$r) }	
	
		#foreach my $r (@ { $self->{FAM}{CROSS_CHECK}{$fam} }) { $canvas->createOval(@$r) }		
		$mw->configure(-title => "HaploPainter V.$self->{GLOB}{VERSION}  -[Family $fam]");
		$param->{INFO_LABEL}->configure(-text => '') ;
	}
	

	elsif ($arg{-modus} eq 'CSV') {
		my $file_name = $arg{-file} or return undef;
		my %t = (
			ascii => '>',
			utf8    => '>:raw:encoding(UTF-8):crlf:utf8',
			utf16le => '>:raw:encoding(UTF-16LE):crlf:utf8',
		);
		
		my $encoding = $t{$param->{ENCODING}};
		
		my @fams;
		if ($arg{-fammode}) { @fams = nsort keys % { $self->{FAM}{PED_ORG} }}
		else { @fams = $fam }
		return unless @fams;
		
		open (FH, $encoding, $file_name) or (ShowInfo("$!: $file_name", 'warning'), return );
			my $head = join "\t", (qw / *FAMILY PERSON FATHER MOTHER GENDER AFFECTION IS_DECEASED IS_SAB_OR_TOP 
			IS_PROBAND IS_ADOPTED ARE_TWINS ARE_CONSANGUINEOUS INNER_SYMBOL_TEXT SIDE_SYMBOL_TEXT 
			LOWER_SYMBOL_TEXT1 LOWER_SYMBOL_TEXT2 LOWER_SYMBOL_TEXT3 LOWER_SYMBOL_TEXT4/);
			
			### write byte of marke (BOM) for Unicode encoded files
			if ( ($param->{ENCODING} ne 'ascii') && $param->{WRITE_BOM}) { print FH "\x{FEFF}" }			
			print FH "$head\n";
						
			foreach my $fam (@fams) {
				my %ped;
				foreach my $r ( @ { $self->{FAM}{PED_ORG}{$fam} } ) {
					next unless $r;
					@_ = @$r;
					foreach (@_[0..17]) { $_ = '' unless defined $_ };
					$ped{$_[0]} = [@_]
				}
				foreach my $pid (nsort keys %ped) {
					@_ = @ { $ped{$pid} }; shift @_;
					$_ = join "\t", ($fam,$pid, @_);
					print FH "$_\n"; 
				}
			}
		close FH;
	}
	
	### render graphic using cairo from the gtk2 environment
	else {				
		return unless $fam;
		my ($surface, $cairo);
		my $file_name = $arg{-file} or return undef;
			
		### exploring coordinates of all drawing elements to find out "bounding box"
		my (%x, %y);	
		foreach my $e (keys %$de) {			
			foreach my $r (@ { $de->{$e} }) {
				for (my $i=0; $i < scalar @$r-1; $i+=2) {
					if ($r->[$i] !~ /^-[a-z]/) {
						$x{$r->[$i]} = 1;
						$y{$r->[$i+1]} = 1
					}
				}
			}
		}
		my @x = sort { $a <=> $b } keys %x;
		my @y = sort { $a <=> $b } keys %y;
		
		### bounding box dimension
		my ($x1_bb, $x2_bb, $y1_bb, $y2_bb) = (@x[0,-1], @y[0,-1]);

		### calculate scale factor based on paper size, paper orientation 
		### and zoom factor during calculation of canvas coordinates
		my $x_pap_mm = $param->{PAPER_SIZE}{$self->{GLOB}{PAPER}}{X};
		my $y_pap_mm = $param->{PAPER_SIZE}{$self->{GLOB}{PAPER}}{Y};
		($x_pap_mm,$y_pap_mm) = ($y_pap_mm,$x_pap_mm)	if $self->{GLOB}{ORIENTATION} =~ /^landscape$/i;	
		
		### Resolution in settings
		my $res = $self->{GLOB}{RESOLUTION_DPI};
		
		### for postscript set to 72 (1 inch = 72 points)
		$res = 72 if $arg{-modus} eq 'PS';
		
		### paper dimension have n pixels at given resolution
		my $x_pap_pix = $x_pap_mm/25.4*$res;
		my $y_pap_pix = $y_pap_mm/25.4*$res;
		
		### border as set in global settings
		my $pix_border = $self->{GLOB}{BORDER}/25.4*$res;				
		
		#### bounding box x and y direction
		my $diffx = $x2_bb - $x1_bb;
		my $diffy = $y2_bb - $y1_bb;

		#### scale factor assuming x adaption versus y direction
		my $f = $x_pap_pix/$diffx;
		$f = $y_pap_pix/$diffy if ($diffy*$f) > $y_pap_pix;	
				
		#### find out dimension of text
		$surface = Cairo::ImageSurface->create ('argb32', $x_pap_pix,$y_pap_pix);		
		$cairo = Cairo::Context->create($surface);						
		$cairo->scale($f,$f);			
		
		### any  text
		foreach my $e (qw /SAB_GENDER MARK_TEXT HAP_TEXT MAP_MARKER_LEFT MAP_MARKER_RIGHT MAP_POS_LEFT MAP_POS_RIGHT TITLE CASE_INFO INNER_SYMBOL_TEXT PROBAND_TEXT/) {
			foreach my $r (@ { $de->{$e} }) {
				my $x = $r->[0]; my $y = $r->[1];	
				my $weight = ''; $weight = 'Bold' if $r->[7][2] eq 'bold'; 
				my $style = ''; $style = 'Italic' if $r->[7][3] eq 'italic';
				my $font_descr_str = join " ", ($r->[7][0], $weight, $style, $r->[7][1]/(96/72) );
				my $pango_layout = Gtk2::Pango::Cairo::create_layout ($cairo);     	
				my $font_desc = Gtk2::Pango::FontDescription->from_string($font_descr_str);
				$pango_layout->set_font_description($font_desc);
				$pango_layout->set_markup ($r->[5]);		
				my ($width, $height) = $pango_layout->get_pixel_size();	
				$x{ $x-($width/2) } = 1;$x{ $x+($width/2) } = 1;
				$y{ $y-($height/2)} = 1;$y{ $y+($height/2) } = 1;	
			}
		}
		undef $surface;
		undef $cairo;
		
		@x = sort { $a <=> $b } keys %x;
		@y = sort { $a <=> $b } keys %y;
		
		### bounding box dimension
		($x1_bb, $x2_bb, $y1_bb, $y2_bb) = (@x[0,-1], @y[0,-1]);
		
		### bounding box x and y direction
		$diffx = $x2_bb - $x1_bb;
		$diffy = $y2_bb - $y1_bb;
		
		### scale factor assuming x adaption versus y direction
		$f = $x_pap_pix/$diffx;
		$f = $y_pap_pix/$diffy if ($diffy*$f) > $y_pap_pix;	
		
		### adding border scaled by factor f
		for ($x1_bb, $y1_bb) { $_-= $pix_border/$f }
		for ($x2_bb, $y2_bb) { $_+= $pix_border/$f }
		
		### recalculating bounding box
		$diffx = $x2_bb - $x1_bb;
		$diffy = $y2_bb - $y1_bb;	
		
		### recalculating factor
		$f = $x_pap_pix/$diffx;
		$f = $y_pap_pix/$diffy if ($diffy*$f) > $y_pap_pix;	
				
		### create differrent surfaces for different output formats
		if ($arg{-modus} eq 'PNG') {				
			$surface = Cairo::ImageSurface->create ('argb32', $x_pap_pix,$y_pap_pix);						
		}
					
		elsif ($arg{-modus} eq 'SVG') {
			$surface = Cairo::SvgSurface->create ($file_name, $x_pap_pix,$y_pap_pix);
		}
		
		elsif ($arg{-modus} eq 'PDF') {
			$surface = Cairo::PdfSurface->create ($file_name, $x_pap_pix,$y_pap_pix);
		}
		elsif ($arg{-modus} eq 'PS') {
			$surface = Cairo::PsSurface->create ($file_name, $diffx,$diffy);
			$surface->set_size($x_pap_pix,$y_pap_pix);
			$surface->dsc_begin_setup;
			$surface->dsc_begin_page_setup;		 			
		} 		 		
		else { ShowInfo("Unknown file format $arg{-modus}\n"), return }
		
		### create cairo context object and scale it to factor $f
		$cairo = Cairo::Context->create($surface);
		$cairo->scale($f,$f);			
		
		### Background box if set in $self->{FAM}{EXPORT_BACKGROUND}
		if ($self->{FAM}{EXPORT_BACKGROUND}{$fam}) {		
			$cairo->set_source_rgb (GetCairoCol($self->{GLOB}{BACKGROUND}));	
			$cairo->paint();			
		}
		
		
		### Lines between COUPLE symbols
		$cairo->set_line_width($l*$z);	
		$cairo->set_source_rgb (GetCairoCol($lnc));
		foreach my $parent_node (keys %{$d->{COUPLE}}) {
			foreach my $ln ( @{$d->{COUPLE}{$parent_node}} ) {
				$cairo->move_to($ln->[0]-$x1_bb,$ln->[1]-$y1_bb);
				for (my $i=2; $i< scalar @$ln-1;$i+=2) {
					$cairo->line_to($ln->[$i]-$x1_bb, $ln->[$i+1]-$y1_bb);
				}
				$cairo->stroke;
			}
		}		  			 
		### Lines between SIB symbols			
		foreach my $id (keys %{$d->{SIB}}) {
			foreach my $ln ( @{$d->{SIB}{$id}} ) {
				$cairo->move_to($ln->[0]-$x1_bb,$ln->[1]-$y1_bb);
				for (my $i=2; $i< scalar @$ln-1;$i+=2) {
					$cairo->line_to($ln->[$i]-$x1_bb, $ln->[$i+1]-$y1_bb);
				}
				$cairo->stroke;
			}
		}		
		### Lines between COUPLE_SIB symbols			
		foreach my $id (keys %{$d->{COUPLE_SIB}}) {
			foreach my $ln ( @{$d->{COUPLE_SIB}{$id}} ) {
				$cairo->move_to($ln->[0]-$x1_bb,$ln->[1]-$y1_bb);
				for (my $i=2; $i< scalar @$ln-1;$i+=2) {
					$cairo->line_to($ln->[$i]-$x1_bb, $ln->[$i+1]-$y1_bb);
				}
				$cairo->stroke;
			}
		}	
		
		### Lines between TWIN symbols			
		foreach my $id (keys %{$d->{TWIN_LINES}}) {
			foreach my $ln ( @{$d->{TWIN_LINES}{$id}} ) {
				$cairo->move_to($ln->[0]-$x1_bb,$ln->[1]-$y1_bb);				
				$cairo->line_to($ln->[2]-$x1_bb,$ln->[3]-$y1_bb);				
				$cairo->stroke;
			}
		}	
		
		### male symbols
		foreach my $r (@{$de->{SYM_MALE}}) { 	  
			my ($x1, $y1, $x2, ) = ($r->[0]-$x1_bb, $r->[1]-$y1_bb, $r->[2]-$r->[0]);
			$cairo->set_line_width($r->[5]);
			$cairo->rectangle($x1, $y1, $x2, $x2);
			$cairo->set_source_rgb (GetCairoCol($r->[9]));
			$cairo->fill_preserve;		  	  	
			$cairo->set_source_rgb (GetCairoCol($r->[7]));
			$cairo->stroke;	
		}				
			 
		### female symbols
			foreach my $r (@{$de->{SYM_FEMALE}}) {
				my ($x1, $y1, $x2) = (   (($r->[0]+$r->[2])/2)-$x1_bb,  (($r->[1]+$r->[3])/2)-$y1_bb, ($r->[2]-$r->[0])/2  );
				my $lw = $r->[5];
				$cairo->set_line_width($lw);
				$cairo->arc($x1, $y1, $x2, 0,360);				
				$cairo->set_source_rgb (GetCairoCol($r->[9]));								
				$cairo->fill_preserve;
				$cairo->set_source_rgb (GetCairoCol($r->[7]));
				$cairo->stroke;		
			}		 
		
		### unknown gender symbols
		foreach my $r (@{$de->{SYM_UNKNOWN}}) {
			my ($x1,$y1,$x2,$y2,$x3,$y3,$x4,$y4 ) = @$r[0..7];
			for ($x1,$x2,$x3,$x4) { $_-=$x1_bb }
			for ($y1,$y2,$y3,$y4) { $_-=$y1_bb }
			$cairo->set_line_width($r->[9]);
			$cairo->move_to($x1, $y1);
			$cairo->line_to($x2, $y2);
			$cairo->line_to($x3, $y3);
			$cairo->line_to($x4, $y4);
			$cairo->close_path();
			$cairo->set_source_rgb (GetCairoCol($r->[13]));
			$cairo->fill_preserve;
			$cairo->set_source_rgb (GetCairoCol($r->[11]));
			$cairo->stroke;	
		}
	
		### stillbirth symbol
		foreach my $r (@{$de->{SYM_STILLBIRTH}}) {
			my ($x1,$y1,$x2,$y2,$x3,$y3) = @$r[0..5];
			for ($x1,$x2,$x3) { $_-=$x1_bb }
			for ($y1,$y2,$y3) { $_-=$y1_bb }
			$cairo->set_line_width($r->[7]);
			$cairo->move_to($x1, $y1);
			$cairo->line_to($x2, $y2);
			$cairo->line_to($x3, $y3);
			$cairo->close_path();
			$cairo->set_source_rgb (GetCairoCol($r->[11]));
			$cairo->fill_preserve;		  	
			$cairo->set_source_rgb (GetCairoCol($r->[9]));
			$cairo->stroke;
		}
	
		### live status line
		foreach my $r (@ { $de->{LIVE_LINE} }) { 
			my ($x1,$y1,$x2,$y2) = @$r[0..3];
			for ($x1,$x2) { $_-=$x1_bb }
			for ($y1,$y2) { $_-=$y1_bb }
			$cairo->set_line_width($r->[5]);
			$cairo->move_to($x1, $y1);
			$cairo->line_to($x2, $y2);
			$cairo->set_source_rgb (GetCairoCol($r->[7]));
			$cairo->stroke; 
		}
		
		
		### IS_ADOPTED
		foreach my $r (@ { $de->{IS_ADOPTED} }) { 
			my ($x1,$y1,$x2,$y2,$x3,$y3,$x4,$y4) = @$r[0..7];
			for ($x1,$x2,$x3,$x4) { $_-=$x1_bb }
			for ($y1,$y2,$y3,$y4) { $_-=$y1_bb }
			$cairo->set_line_width($r->[9]);
			$cairo->move_to($x1, $y1);
			$cairo->line_to($x2, $y2);
			$cairo->line_to($x3, $y3);
			$cairo->line_to($x4, $y4);
			$cairo->set_source_rgb (GetCairoCol($r->[11]));
			$cairo->stroke; 
		}
		
		### haplotype bars
		for my $bar (qw /HAP_BAR_NI HAP_BAR/) {
			foreach my $r (@ { $de->{$bar} }) { 
				my ($x1, $y1, $x2, $y2 ) = ($r->[0]-$x1_bb, $r->[1]-$y1_bb, $r->[2]-$r->[0], $r->[3]-$r->[1]);
				$cairo->rectangle($x1, $y1, $x2, $y2);
				$cairo->set_line_width($r->[5]);
				if ($r->[9]) {
					$cairo->set_source_rgb (GetCairoCol($r->[9]));
					$cairo->fill_preserve;
				}
				$cairo->set_source_rgb (GetCairoCol($r->[7]));
				$cairo->stroke;	
			}
		}
		
		### haplotype bounding boxes
		foreach my $r (@ { $de->{HAP_BOX} }) { 
			my ($x1, $y1, $x2, $y2 ) = ($r->[0]-$x1_bb, $r->[1]-$y1_bb, $r->[2]-$r->[0], $r->[3]-$r->[1]);
			$cairo->rectangle($x1, $y1, $x2, $y2);
			$cairo->set_line_width($r->[5]);
			$cairo->set_source_rgb (GetCairoCol($r->[7]));
			#$cairo->fill_preserve;
			#$cairo->set_source_rgb (GetCairoCol($r->[7]));
			$cairo->stroke;	
		}
		
		
		### any  text
		foreach my $e (qw /SAB_GENDER MARK_TEXT HAP_TEXT MAP_MARKER_LEFT MAP_MARKER_RIGHT MAP_POS_LEFT MAP_POS_RIGHT TITLE CASE_INFO INNER_SYMBOL_TEXT PROBAND_TEXT/) {
			foreach my $r (@ { $de->{$e} }) {
				my $x = $r->[0]-$x1_bb;
				my $y = $r->[1]-$y1_bb;
				#print "ALIGN=$r->[3]\n";
				### 96dpi/72dpi is empirical found to right scale the panda font size
				### may be this code has to be adopted to current display resolution?
				my $weight = ''; $weight = 'Bold' if $r->[7][2] eq 'bold'; 
				my $style = ''; $style = 'Italic' if $r->[7][3] eq 'italic';
				my $font_descr_str = join " ", ($r->[7][0], $weight, $style, $r->[7][1]/(96/72) );
				my $pango_layout = Gtk2::Pango::Cairo::create_layout ($cairo);     	
				my $font_desc = Gtk2::Pango::FontDescription->from_string($font_descr_str);
				$pango_layout->set_font_description($font_desc);
				$pango_layout->set_markup ($r->[5]);
				
				my ($width, $height) = $pango_layout->get_pixel_size();
				
				### pango set_alignment does not work!?!?!
				### work arround
				if ($r->[3] eq 'w') { $cairo->move_to($x,$y-($height/2)) }
				elsif ($r->[3] eq 'e') { $cairo->move_to($x-$width,$y-($height/2)) }
				elsif ($r->[3] eq 'center') { $cairo->move_to($x-($width/2),$y-($height/2)) }
				
				$cairo->set_source_rgb (GetCairoCol($r->[9]));
				Gtk2::Pango::Cairo::show_layout ($cairo, $pango_layout);
			}	
		}
		
		### proband arrow
		foreach my $r (@ { $de->{ARROWS} }) { 
			my ($x1,$y1,$x2,$y2) = @$r[0..3];
			for ($x1,$x2) { $_-=$x1_bb }
			for ($y1,$y2) { $_-=$y1_bb }
			$cairo->set_line_width($r->[5]);
			$cairo->set_source_rgb (GetCairoCol($r->[7]));
			
			### drawing arrow shape using trigonomic functions and the assumption
			### that the arrow angle beeing 45 degree		
			my $d1=$self->{FAM}{ARROW_DIST1}{$fam}*$z;
			my $d2=$self->{FAM}{ARROW_DIST2}{$fam}*$z;
			my $d3=$self->{FAM}{ARROW_DIST3}{$fam}*$z;
						
			my $b = sqrt ( ($d2*$d2) + ($d3*$d3) );
			my $c = sqrt ( ($d3*$d3) + (($d2-$d1)*($d2-$d1)) );			
			my ($aq,$bq,$cq) = ($d1*$d1,$b*$b,$c*$c);						
			my $alpha2 = 45 - rad2deg(acos(($aq+$bq-$cq)/(2*$d1*$b)));			
			my $x3 = cos(deg2rad($alpha2))*$b;
			my $y3 = sqrt ($bq-($x3*$x3));
			my $x4 = sqrt (($d1*$d1)/2);
			
			$cairo->move_to($x1, $y1);
			$cairo->line_to($x2-$x4, $y2+$x4);
			$cairo->stroke; 			
			$cairo->line_to($x2-$x3, $y2+$y3);
			$cairo->line_to($x2,$y2);
			$cairo->line_to($x2-$y3, $y2+$x3);
			$cairo->line_to($x2-$x4, $y2+$x4);
			$cairo->close_path();			
			$cairo->fill;
			$cairo->stroke; 						
		}
		
		### create graphics
		$cairo->show_page;
				
		### PNG slightly differ in syntax --> extra command 
		if ($arg{-modus} eq 'PNG') {			
			$surface->write_to_png ($file_name);		
		}
		
		### otherwise the file handle is not closed properly!
		### (i found no methods for destroying or finishing cairo/surface ...)
		undef $surface;
		undef $cairo;		
	}
	1;
}

#================
sub GetCairoCol {
#================
	my $col = shift @_ || return (0,0,0);
	if ($col =~ /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/) {
		return (hex($1)/255,hex($2)/255,hex($3)/255);
	}
	ShowInfo("Error reading color: $col - is substituted to black!\n");
	return (0,0,0)
}

#===============
sub SetSymbols {
#===============	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $m = $self->{FAM}{MATRIX}{$fam} or return;
	my $z = $self->{FAM}{ZOOM}{$fam};
	my $l = $self->{FAM}{SYMBOL_LINE_WIDTH}{$fam};
	my $lnc = $self->{FAM}{LINE_COLOR}{$fam};
	my $s = $param->{SHOW_GRID};
	my $slnc = $self->{FAM}{SYMBOL_LINE_COLOR}{$fam};
	my $f1 = $self->{FAM}{FONT1}{$fam};
	my $f2 = $self->{FAM}{FONT_INNER_SYMBOL}{$fam};
	my $f3 = $self->{FAM}{FONT_HEAD}{$fam};
	my $f4 = $self->{FAM}{FONT_PROBAND}{$fam};
	my $f5 = $self->{FAM}{FONT_MARK}{$fam}; 
	my $font1 = [ $f1->{FAMILY},$f1->{SIZE}*$z , $f1->{WEIGHT},$f1->{SLANT} ];
	my $font2 = [ $f2->{FAMILY},$f2->{SIZE}*$z , $f2->{WEIGHT},$f2->{SLANT} ];
	my $head1 = [ $f3->{FAMILY},$f3->{SIZE}*$z , $f3->{WEIGHT},$f3->{SLANT} ];
	my $font4 = [ $f4->{FAMILY},$f4->{SIZE}*$z , $f4->{WEIGHT},$f4->{SLANT} ];
	my $font5 = [ $f5->{FAMILY},$f5->{SIZE}*$z , $f5->{WEIGHT},$f5->{SLANT} ];
	my $as = $self->{FAM}{ALIVE_SPACE}{$fam};
	my $ci = $self->{FAM}{CASE_INFO}{$fam};
	my $as1 = $self->{FAM}{ADOPTED_SPACE1}{$fam};
	my $as2 = $self->{FAM}{ADOPTED_SPACE2}{$fam};
	my $de = $self->{FAM}{DRAW_ELEMENTS}{$fam}{CANVAS} = {};
	my $ab1 = $self->{FAM}{ARROW_SYM_DIST}{$fam};
	my $arl = $self->{FAM}{ARROW_LENGTH}{$fam};
	my $dist1 = $self->{FAM}{ARROW_DIST1}{$fam};
	my $dist2 = $self->{FAM}{ARROW_DIST2}{$fam};
	my $dist3 = $self->{FAM}{ARROW_DIST3}{$fam};				
	my $plw = $self->{FAM}{ARROW_LINE_WIDTH}{$fam};
	my $plc = $self->{FAM}{ARROW_COLOR}{$fam};
	my $sz = $self->{FAM}{SYMBOL_SIZE}{$fam}/2;
	my $slcs = $self->{FAM}{SYMBOL_LINE_COLOR_SET}{$fam};
	my %t= (qw/0 u 1 m 2 f/);
	my %save;
	
	### adapt Y achsis of drawing elements dependent of haplotypes and drawing style
	CanvasTrimYdim();
	
	### Title		
	if (! $self->{FAM}{TITLE_X}{$fam}) {  
		($_) = sort { $a <=> $b } keys %{$m->{YX2P}} or return;
		@_ = sort { $a <=> $b } keys % { $m->{YX2P}{$_} } or return;
		$self->{FAM}{TITLE_X}{$fam} = ($_[0]+$_[-1])/2;
		$self->{FAM}{TITLE_Y}{$fam} = $_-3;
	}	
	
	if ($self->{FAM}{SHOW_HEAD}{$fam} ) {	 					
		if (! $self->{FAM}{TITLE}{$fam}) {  $self->{FAM}{TITLE}{$fam} = "Family $fam" }				
		push @ { $de->{TITLE} }, [
			$self->{FAM}{TITLE_X}{$fam}*$self->{FAM}{GITTER_X}{$fam}*$z, $self->{FAM}{TITLE_Y}{$fam}*$self->{FAM}{GITTER_Y}{$fam}*$z, 			
			-anchor => 'center', -text => $self->{FAM}{TITLE}{$fam} , 
			-font => $head1, -fill => $self->{FAM}{FONT_HEAD}{$fam}{COLOR}, -tags => [ 'TEXT' , 'HEAD', 'TAG' ]
		];		
	}
		
	### Zeichnen aller Personen-bezogenen Elemente
	### Drawing of individual related elements	
	foreach my $Y (keys % { $m->{YX2P} }) {
		foreach my $X (keys % { $m->{YX2P}{$Y} }) {
			my $p = $m->{YX2P}{$Y}{$X};
			if ($save{$p}) {next}
			$save{$p} = 1;
			my ($sex, $aff) = ( $self->{FAM}{SID2SEX}{$fam}{$p}, $self->{FAM}{SID2AFF}{$fam}{$p} );				
			my ($cx, $cy) = ($X*$self->{FAM}{GITTER_X}{$fam}, $Y*$self->{FAM}{GITTER_Y}{$fam});
			my $col = $self->{FAM}{AFF_COLOR}{$fam}{$aff};
			my $slnc_new = $col;
			if ($col eq '#ffffff') { $slnc_new = $slnc }
			elsif ($slcs) { $slnc_new= $slnc }
	
			# by setting affected status = 9, an individual can become invisible
			if ($aff == 9) {
				$slnc_new = '#ffffff';
				#next;
				
				#push @ { $de->{LIVE_LINE} }, [
				#	($cx-$sz)*$z, $cy*$z,
				#	($cx+$sz)*$z, $cy*$z,
				#	-width => $l*$z, -fill => $slcs
				#];
				
				push @ { $de->{INNER_SYMBOL_TEXT} }, [
				    $cx*$z, $cy*$z,
				    -anchor => 'center', -text => '?', 
				    -font => $head1, -fill => $slcs, -tags => [ 'TEXT', 'INNER_SYMBOL_TEXT' ]
				];
			} 
			
			### stillbirth
			elsif ($self->{FAM}{IS_SAB_OR_TOP}{$fam}{$p}) {								
				push @ { $de->{SYM_STILLBIRTH} }, [
					($cx-$sz)*$z, $cy*$z,
					$cx*$z, ($cy-$sz)*$z,
					($cx+$sz)*$z, $cy*$z,
					-width => $l*$z, -outline => $slnc_new,-fill => $col, -tags => [ 'SYMBOL', "SYM-$p", 'TAG' ]
				];		
			}
							
			### male
			elsif ($sex == 1) {
				push @ { $de->{SYM_MALE} }, [
					($cx-$sz)*$z, ($cy-$sz)*$z,
					($cx+$sz)*$z, ($cy+$sz)*$z ,
					-width => $l*$z, -outline => $slnc_new, -fill => $col, -tags => [ 'SYMBOL', "SYM-$p" , 'TAG' ] 
				];																				
			}
			### female
			elsif ($sex == 2) {				
				push @ { $de->{SYM_FEMALE} }, [
					($cx-$sz)*$z, ($cy-$sz)*$z,
					($cx+$sz)*$z, ($cy+$sz)*$z ,
					-width => $l*$z, -outline => $slnc_new, -fill => $col, -tags => [ 'SYMBOL', "SYM-$p", 'TAG' ]
				];						
			}
						
			### unknown gender
			else {
				push @ { $de->{SYM_UNKNOWN} }, [
					($cx-$sz*sqrt(2))*$z, $cy*$z,
					$cx*$z, ($cy-$sz*sqrt(2))*$z,
					($cx+$sz*sqrt(2))*$z, $cy*$z,
					$cx*$z, ($cy+$sz*sqrt(2))*$z,
					-width => $l*$z, -outline => $slnc_new,-fill => $col, -tags => [ 'SYMBOL', "SYM-$p", 'TAG' ]
				];		
			}			
		
			### show available text inside symbols if param: INNER_SYMBOL_TEXT is set.
			### for now disabled for SAB/TAP symbols because the inner space for that symbol
			### is to small to fit text properly
			if ($self->{FAM}{SHOW_INNER_SYBOL_TEXT}{$fam} && defined $self->{FAM}{INNER_SYMBOL_TEXT}{$fam}{$p} &&
				! $self->{FAM}{IS_SAB_OR_TOP}{$fam}{$p}) {
					push @ { $de->{INNER_SYMBOL_TEXT} },[
					$cx*$z, $cy*$z,
					-anchor => 'center', -text => $self->{FAM}{INNER_SYMBOL_TEXT}{$fam}{$p},
					-font => $font2, -fill => $self->{FAM}{FONT_INNER_SYMBOL}{$fam}{COLOR}, -tags => [ 'TEXT', "INNER_SYMBOL_TEXT-$p", 'INNER_SYMBOL_TEXT' ]
				];
			}
			
			### live status
			if ($self->{FAM}{IS_DECEASED}{$fam}{$p}) {				
				### spontaneous abort or termination of pregnancy
				### are calculated different
				if ($self->{FAM}{IS_SAB_OR_TOP}{$fam}{$p}) {
					push @ { $de->{LIVE_LINE} }, [						
						($cx-$sz)*$z, ($cy+($sz/2))*$z,
						($cx+($sz*3/4))*$z, ($cy-($sz/2)-($sz*3/4))*$z,																						
						-width => $l*$z,-fill => $lnc
					]					
				}			
				
				elsif (defined $self->{FAM}{INNER_SYMBOL_TEXT}{$fam}{$p}) {
					
					my $f = $sz/sqrt(2);
					my ($x1,$y1,$x2,$y2);
					my $as_i = 3;														
					
					if ($sex==1) {
						($x1, $y1) = ($cx-$sz,$cy+$sz);
						($x2, $y2) = ($cx+$sz,$cy-$sz);
					}
					elsif (!$sex || $sex==2) {
						($x1, $y1) = ($cx-$f,$cy+$f);
						($x2, $y2) = ($cx+$f,$cy-$f);
					}
					
					push @ { $de->{LIVE_LINE} }, [
						($x1-$as)*$z,   ($y1+$as)*$z ,
						($x1+$as_i)*$z, ($y1-$as_i)*$z ,
						-width => $l*$z,-fill => $lnc
					];
					
					push @ { $de->{LIVE_LINE} }, [
						($x2+$as)*$z,   ($y2-$as)*$z ,
						($x2-$as_i)*$z, ($y2+$as_i)*$z ,
						-width => $l*$z,-fill => $lnc	
					];
											
				} else {
					push @ { $de->{LIVE_LINE} }, [
						($cx-$sz-$as)*$z, ($cy+$sz+$as)*$z ,
						($cx+$sz+$as)*$z, ($cy-$sz-$as)*$z ,
						-width => $l*$z,-fill => $lnc
					]
				}
			}
			          
			### Individual identifier and case information
			foreach my $col ( 1 .. 5 ) {
				if ($self->{FAM}{CASE_INFO_SHOW}{$fam}{$col} && $ci->{COL_TO_NAME}{$col} && $aff != 9) {
					my $yp = ($cy+$sz)*$z + $f1->{SIZE}*$z + ($col-1)*$f1->{SIZE}*$z;
					my $name = $ci->{COL_TO_NAME}{$col};					
					next if ! defined $ci->{PID}{$p}{$name};
					my $y_pid = sprintf ("%0.0f",$yp+($f1->{SIZE}*$z)/2);
					
					push @ { $de->{CASE_INFO} }, [	
						$cx*$z,  $yp,
						-anchor => 'center', -text => $ci->{PID}{$p}{$name} ,
						-font => $font1, -fill => $f1->{COLOR}, -tags => [ 'TEXT', "TEXT-$p" ]
					];
				}
			}
			
			### Proband status fild
			if ($self->{FAM}{IS_PROBAND}{$fam}{$p}) {											
				my $x1 = ($cx-$sz-$ab1);
				my $y1 = ($cy+($sz/3));				
				$x1-= $ab1 if $self->{FAM}{IS_ADOPTED}{$fam}{$p};				
				my $x2 = $x1-$arl;
				my $y2 = $y1+$arl;
								
				push @ { $de->{ARROWS} }, [
					$x2*$z, $y2*$z, $x1*$z, $y1*$z, -width => $plw*$z,-fill => $plc, -arrow => 'last', -arrowshape => [ $dist1*$z, $dist2*$z, $dist3*$z]
				];
				
				push @ { $de->{PROBAND_TEXT} }, [	
						($x2*$z) - ($f4->{SIZE}*$z)/2,  $y2*$z,-anchor => 'center', 
						-text => $self->{FAM}{PROBAND_SIGN}{$fam} ,-font => $font4, -fill => $f4->{COLOR}
				]; 				
			}
			
			
			
			### Marked field
			if (defined $self->{FAM}{SIDE_SYMBOL_TEXT}{$fam}{$p}) {			
				push @ { $de->{MARK_TEXT} }, [											
					($cx-$sz-($f5->{SIZE}/1.5))*$z,  ($cy-$sz-($f5->{SIZE}/1.5))*$z,-anchor => 'center', 										
					-text => $self->{FAM}{SIDE_SYMBOL_TEXT}{$fam}{$p} ,-font => $font5, -fill => $f5->{COLOR}
				];				
			}
			
			### adopted
			if (defined $self->{FAM}{IS_ADOPTED}{$fam}{$p}) {		
				my @l1 = (
					$cx-$sz+$as2, $cy+$sz+$as1,$cx-$sz-$as1, $cy+$sz+$as1,
					$cx-$sz-$as1, $cy-$sz-$as1,$cx-$sz+$as2, $cy-$sz-$as1
				);				
				my @l2 = (
					$cx+$sz-$as2, $cy+$sz+$as1,$cx+$sz+$as1, $cy+$sz+$as1,
					$cx+$sz+$as1, $cy-$sz-$as1,$cx+$sz-$as2, $cy-$sz-$as1
				);						
				foreach (@l1, @l2) { $_*= $z }
				push @ { $de->{IS_ADOPTED} }, [ @l1, -width => $l*$z,-fill => $lnc ];
				push @ { $de->{IS_ADOPTED} }, [ @l2, -width => $l*$z,-fill => $lnc ];				
			}
			
			### show gender as text under sab
			if ($self->{FAM}{IS_SAB_OR_TOP}{$fam}{$p} && $self->{FAM}{SHOW_GENDER_SAB}{$fam}) {
				push @ { $de->{SAB_GENDER} }, [											
					$cx*$z,  ($cy+($f4->{SIZE}/1.5))*$z,-anchor => 'center', 										
					-text => $t{$sex} ,-font => $font4, -fill => $f4->{COLOR}
				];
				
			}
		}
	}
}
	
### set all drawing elements in respect of haplotypes
#=============
sub SetHaplo {
#=============
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $m = $self->{FAM}{MATRIX}{$fam};
	my $h = $self->{FAM}{HAPLO}{$fam} or return;
	return unless keys %{$self->{FAM}{HAPLO}{$fam}};
	my $z = $self->{FAM}{ZOOM}{$fam};
	my $f1 = $self->{FAM}{FONT1}{$fam};
	my $fh = $self->{FAM}{FONT_HAPLO}{$fam};
	my $l = $self->{FAM}{SYMBOL_LINE_WIDTH}{$fam};
	my $lnc = $self->{FAM}{LINE_COLOR}{$fam};
	my $lw = $self->{FAM}{HAPLO_TEXT_LW}{$fam};
	my $td1 = ($fh->{SIZE}*$z) + ($lw*$fh->{SIZE}*$z);
	my $font1  =  [ $f1->{FAMILY},$f1->{SIZE}*$z ,$f1->{WEIGHT},$f1->{SLANT} ];
	my $font_haplo =  [ $fh->{FAMILY},$fh->{SIZE}*$z , $fh->{WEIGHT}, $fh->{SLANT} ];
	my $hw = $self->{FAM}{HAPLO_WIDTH}{$fam};
	my $hwni = $self->{FAM}{HAPLO_WIDTH_NI}{$fam};
	my $hs = $self->{FAM}{HAPLO_SPACE}{$fam};
	my $hlw = $self->{FAM}{HAPLO_LW}{$fam};
	my $un = $self->{FAM}{HAPLO_UNKNOWN}{$fam};
	my $de = $self->{FAM}{DRAW_ELEMENTS}{$fam}{CANVAS};
	my $sz = $self->{FAM}{SYMBOL_SIZE}{$fam};
	my $gy = $self->{FAM}{GITTER_Y}{$fam};
	my $ys = $self->{FAM}{Y_SPACE}{$fam};					
	my $lsy = $self->{FAM}{LINE_SIBS_Y}{$fam};
	my $yse = $self->{FAM}{Y_SPACE_EXTRA}{$fam};
	
	### find most left and right X matrix position for legend drawing
	my @X_GLOB; push @X_GLOB,( keys % { $m->{YX2P}{$_} }) foreach keys % { $m->{YX2P} }; 
	@X_GLOB = sort { $a <=> $b } @X_GLOB;

	### find last valid index ($i2) and number of drawing elements ($i3)
	my ($i1, $i2, $i3) = (0,0,0);
	foreach (@{$h->{DRAW}}) {
		if ($_) { $i2 = $i1 ; $i3++ } $i1++
	}

	### find disabled or hidden colors
	my %Hide;
	if ($self->{FAM}{PED_ORG}{$fam}) {
		foreach (@{$self->{FAM}{PED_ORG}{$fam}}) {
			next unless $_;
			my $pid = @$_[0];
			for my $mp ( 'M','P') {
				if ($h->{PID}{$pid}{$mp}{HIDE}) {
					foreach ( @{$h->{PID}{$pid}{$mp}{BAR}}) {
						$Hide{@$_[1]} = 1 if @$_[1] ne $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam}
					}
				}
			}
		}
	}
	
	### number of text elements to draw below symbols
	my $ccc=1; for (5,4,3,2,1) { if ($self->{FAM}{CASE_INFO_SHOW}{$fam}{$_}) { $ccc=$_+1;last  } }
	my $text = $f1->{SIZE}*$ccc*$z;				

	### drawing haplotypes and legend
	foreach my $Y (keys % { $m->{YX2P} }) {
		my @X = sort { $a <=> $b } keys % { $m->{YX2P}{$Y} };
		my $cy = $Y*$self->{FAM}{GITTER_Y}{$fam} + $lw*$z*2;
		my $curr_y = ($cy+$sz)*$z;
		
		foreach my $X (@X) {
			my $p = $m->{YX2P}{$Y}{$X};		
			my $cx = $X*$self->{FAM}{GITTER_X}{$fam};		
			
			### haplotypes as bar
			if ( $h->{PID}{$p}{P}{TEXT} ) {
				if ($self->{FAM}{SHOW_HAPLO_BAR}{$fam}) {
					my $td = $td1;
					my ($col, $inf, $ncol, $ninf, $out, $lr, $fill, $al, $x1, $x2, $y1, $y2 );
						
					### shrink bar to value of Y_SPACE 
					if (! BarTextOk()) {									
						my $free_space = (($gy*$ys)-(2*$sz)-$text-$lsy-$yse)*$z;
						$td = $free_space/$i3;
					}

					my $y = $curr_y + $text + $td;
					
					foreach my $PM ( 'P', 'M') {
						my ($f, $cc, $nif, $nexti) = (1,0,0);
						if ($PM eq 'M') { $lr = -1 } else { $lr = 1 }

						for (my $i=0; $i <= $i2;$i++) {
							next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
							$al = $h->{PID}{$p}{$PM}{TEXT}[$i];
							($inf,$col) = @{ $h->{PID}{$p}{$PM}{BAR}[$i] };
							next if $Hide{$col};
							### draw bars as not-informative
							### NI-0: no genotypes there at all
							### NI-1: several lost genotypes
							### NI-2: genotyped but declared as not-informative by hand 
							### NI-3: genotyped but declared as not-informative automatically
							if (
								( ($inf eq 'NI-0') && $self->{FAM}{SHOW_HAPLO_NI_0}{$fam} ) ||
								( ($inf eq 'NI-1') && $self->{FAM}{SHOW_HAPLO_NI_1}{$fam} ) ||
								( ($inf eq 'NI-2') && $self->{FAM}{SHOW_HAPLO_NI_2}{$fam} ) ||
								( ($inf eq 'NI-3') && $self->{FAM}{SHOW_HAPLO_NI_3}{$fam} )
							) {
								$out = $fill = $self->{FAM}{HAPLO_UNKNOWN_COLOR}{$fam};
								if ( $self->{FAM}{SHOW_HAPLO_TEXT}{$fam} && ! $self->{FAM}{ALLELES_SHIFT}{$fam}) { $cc++; next }
								($x1, $x2) = ( ($cx-($lr*$hs)-($hwni/2))*$z, ($cx-($lr*$hs)+($hwni/2))*$z );
								$nif = 1;
							} else {
								$out = $fill = $col;
								$nif = 0;
								($x1, $x2) = ( ($cx-($lr*$hs)-($hw/2))*$z, ($cx-($lr*$hs)+($hw/2))*$z );
							}

							undef $fill if ! $self->{FAM}{FILL_HAPLO}{$fam};
							
							
							if (! $self->{FAM}{HAPLO_SEP_BL}{$fam}) {								
								if ($i != $i2) {
									### next element to draw
									my $i4; for ($i4=$i+1; $i4 <= $i2;$i4++) {last if $self->{FAM}{HAPLO}{$fam}{DRAW}[$i4]}
									($ninf,$ncol) = @{ $h->{PID}{$p}{$PM}{BAR}[$i4] };
									if (
										( ($ninf eq 'NI-0') && $self->{FAM}{SHOW_HAPLO_NI_0}{$fam} ) ||
										( ($ninf eq 'NI-1') && $self->{FAM}{SHOW_HAPLO_NI_1}{$fam} ) ||
										( ($ninf eq 'NI-2') && $self->{FAM}{SHOW_HAPLO_NI_2}{$fam} ) ||
										( ($ninf eq 'NI-3') && $self->{FAM}{SHOW_HAPLO_NI_3}{$fam} )
									) { $nexti = 1 }
									else { $nexti = 0 }
									if ( ($col eq $ncol) && ($nif == $nexti) ) {
										$f++; $cc++; next
									} else {
										($y1, $y2) = ( $y + ($cc-$f)*$td,  $y + $cc*$td ); $f = 1
									}
								} else {
									($y1, $y2) = ( $y + ($cc-$f)*$td,  $y + $cc*$td ); $f = 1
								}
							} else {
								($y1, $y2) = ( $y + ($cc-1)*$td,  $y + $cc*$td )
							}
							### different arrays for informative versus not-informative haplotypes
							### to facilitate right drawing order 
							if (! $nif) {																
								push @ { $de->{HAP_BAR} }, [
									$x1 , $y1, $x2 , $y2,
									-width => $hlw*$z, -outline => $out,
									-fill => $fill, -tags => [ "BAR", "BAR1-$p" ]
								]
							}
							else {
								push @ { $de->{HAP_BAR_NI} }, [
									$x1 , $y1, $x2 , $y2,
									-width => $hlw*$z, -outline => $out,
									-fill => $fill, -tags => [ "BAR", "BAR1-$p"]
								]
							}
							
							$cc++;
	
						}
					}
				}

				### haplotypes as text
				if ($self->{FAM}{SHOW_HAPLO_TEXT}{$fam}) {
					my $cc = 0;
					my $col;
					my $sh = $self->{FAM}{ALLELES_SHIFT}{$fam};
					my ($x1, $x2) = ( ($cx-$hs-$sh)*$z, ($cx+$hs+$sh)*$z );
					
					#my $y = $pmy[-1] + $f1->{SIZE}*$z + $td1/2;
					my $y = $curr_y + $text + $td1/2;
				
					### paternal haplotype
					for (my $i=0; $i <= $#{ $h->{PID}{$p}{P}{TEXT} };$i++) {
						next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
						my $inf = $h->{PID}{$p}{P}{BAR}[$i][0];
						
						if (
								$self->{FAM}{SHOW_COLORED_TEXT}{$fam} && ! (
								( ($inf eq 'NI-0') && $self->{FAM}{SHOW_HAPLO_NI_0}{$fam} ) ||
								( ($inf eq 'NI-1') && $self->{FAM}{SHOW_HAPLO_NI_1}{$fam} ) ||
								( ($inf eq 'NI-2') && $self->{FAM}{SHOW_HAPLO_NI_2}{$fam} ) ||
								( ($inf eq 'NI-3') && $self->{FAM}{SHOW_HAPLO_NI_3}{$fam} ) )
							) { $col = $h->{PID}{$p}{P}{BAR}[$i][1] } else { $col = $fh->{COLOR} }
						
						
						$h->{PID}{$p}{P}{TEXT}[$i] =~ s/@/$self->{FAM}{HAPLO_UNKNOWN}{$fam}/;
						push @ { $de->{HAP_TEXT} }, [
							$x1, $y+ ($cc*$td1),
							-anchor => 'center', -text => $h->{PID}{$p}{P}{TEXT}[$i] ,
							-font => $font_haplo, -fill => $col, -tags => [ 'ALLEL', "ALLEL-P-$i-$p" ]
						];
						$cc++
					}


					$cc = 0;
					### maternal haplotype
					for (my $i=0; $i <= $#{ $h->{PID}{$p}{M}{TEXT} };$i++) {
						next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
						my $inf = $h->{PID}{$p}{M}{BAR}[$i][0];
						if (
								$self->{FAM}{SHOW_COLORED_TEXT}{$fam} && ! (
								( ($inf eq 'NI-0') && $self->{FAM}{SHOW_HAPLO_NI_0}{$fam} ) ||
								( ($inf eq 'NI-1') && $self->{FAM}{SHOW_HAPLO_NI_1}{$fam} ) ||
								( ($inf eq 'NI-2') && $self->{FAM}{SHOW_HAPLO_NI_2}{$fam} ) ||
								( ($inf eq 'NI-3') && $self->{FAM}{SHOW_HAPLO_NI_3}{$fam} ) )
							) { $col = $h->{PID}{$p}{M}{BAR}[$i][1] } else { $col = $fh->{COLOR} }
						
						
						$h->{PID}{$p}{P}{TEXT}[$i] =~ s/@/$self->{FAM}{HAPLO_UNKNOWN}{$fam}/;
						$h->{PID}{$p}{M}{TEXT}[$i] =~ s/@/$self->{FAM}{HAPLO_UNKNOWN}{$fam}/;
						push @ { $de->{HAP_TEXT} }, [
							$x2, $y + ($cc*$td1),
							-anchor => 'center', -text => $h->{PID}{$p}{M}{TEXT}[$i],
							-font => $font_haplo, -fill => $col, -tags => [ 'ALLEL', "ALLEL-M-$i-$p" ]
						];
						$cc++
					}
				}

				### haplotypes as bounding box
				if ($self->{FAM}{SHOW_HAPLO_BBOX}{$fam} && $h->{PID}{$p}{BOX}) {
					my ($x1, $x2) = (($cx-$self->{FAM}{BBOX_WIDTH}{$fam})*$z,($cx+$self->{FAM}{BBOX_WIDTH}{$fam})*$z);
					my ($y1, $y2);
					my $f = 1;
					my $cc = 0;
					my $td = $td1;
					if (! $self->{FAM}{SHOW_HAPLO_TEXT}{$fam} ) {
						$td = ($self->{FAM}{Y_SPACE}{$fam}-3.5)*$self->{FAM}{GITTER_Y}{$fam}*$z/$i3;
					}
					
					#my $y = $pmy[-1] + $f1->{SIZE}*$z + $td;
					my $y = $curr_y + $text + $td;
					
					for (my $i=0; $i <= $i2;$i++) {
						next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
						unless ($h->{PID}{$p}{BOX}[$i]) { $cc++; next }
 						if ($i != $i2) {
							if ( $h->{PID}{$p}{BOX}[$i+1] ) {
								$f++; $cc++; next
							} else {
								($y1, $y2) = ( $y + ($cc-$f)*$td,  $y + $cc*$td ); $f = 1
							}
						} else {
							($y1, $y2) = ( $y + ($cc-$f)*$td,  $y + $cc*$td ); $f = 1
						}
												
						push @ { $de->{HAP_BOX} }, [
							$x1, $y1, $x2, $y2,
							-width => $hlw*$z, -outline => '#000000',
							-tags => [ 'BOX', "BOX-$p", 'TAG' ]
						];	
						$cc++
					}
				}
			}
		}

		### map information
		if (@X && $self->{FAM}{MAP}{$fam}) {
			my $cc = 0;
			
			
			#my $y = $pmy[-1] + $f1->{SIZE}*$z + $td1/2;
			my $y = $curr_y + $text + $td1/2;
			
			if ($self->{FAM}{SHOW_MARKER}{$fam}) {
				
				### marker left side
				if ($self->{FAM}{SHOW_LEGEND_LEFT}{$fam}) {
					$cc = 0; 
					my $x;
					if ($self->{FAM}{ALIGN_LEGEND}{$fam}) {
						$x = ( ($X_GLOB[0]*$self->{FAM}{GITTER_X}{$fam}) - $self->{FAM}{LEGEND_SHIFT_LEFT}{$fam} ) * $z;
					} else {
						$x = ( ($X[0]*$self->{FAM}{GITTER_X}{$fam}) - $self->{FAM}{LEGEND_SHIFT_LEFT}{$fam} ) * $z;
					}												 
					for (my $i=0; $i <= $#{ $self->{FAM}{MAP}{$fam}{MARKER} };$i++) {
						next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
						push @ { $de->{MAP_MARKER_LEFT} }, [	
							$x, $y + ($cc*$td1),
							-anchor => 'w', -text => $self->{FAM}{MAP}{$fam}{MARKER}[$i] ,
							-font => $font_haplo, -fill => $fh->{COLOR}
						];
						$cc++
					}
				}
				
				### marker right side
				if ($self->{FAM}{SHOW_LEGEND_RIGHT}{$fam}) {
					$cc = 0; 
					my $x;
					if ($self->{FAM}{ALIGN_LEGEND}{$fam}) {
						$x = ( ($X_GLOB[-1]*$self->{FAM}{GITTER_X}{$fam}) + $self->{FAM}{LEGEND_SHIFT_RIGHT}{$fam} ) * $z;
					} else {
						$x = ( ($X[-1]*$self->{FAM}{GITTER_X}{$fam}) + $self->{FAM}{LEGEND_SHIFT_RIGHT}{$fam} ) * $z;
					}																	 
					for (my $i=0; $i <= $#{ $self->{FAM}{MAP}{$fam}{MARKER} };$i++) {
						next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
						push @ { $de->{MAP_MARKER_RIGHT} }, [	
							$x, $y + ($cc*$td1),
							-anchor => 'w', -text => $self->{FAM}{MAP}{$fam}{MARKER}[$i] ,
							-font => $font_haplo, -fill => $fh->{COLOR}
						];
						$cc++
					}
				}			
			
			}

			if ($self->{FAM}{SHOW_POSITION}{$fam}) {				
				
				### position left side
				if ($self->{FAM}{SHOW_LEGEND_LEFT}{$fam}) {
					$cc = 0; 
					my $x;
					if ($self->{FAM}{ALIGN_LEGEND}{$fam}) {
						$x = ( ($X_GLOB[0]*$self->{FAM}{GITTER_X}{$fam}) - $self->{FAM}{LEGEND_SHIFT_LEFT}{$fam} + $self->{FAM}{MARKER_POS_SHIFT}{$fam} ) * $z;
					} else {
						$x = ( ($X[0]*$self->{FAM}{GITTER_X}{$fam}) - $self->{FAM}{LEGEND_SHIFT_LEFT}{$fam} + $self->{FAM}{MARKER_POS_SHIFT}{$fam} ) * $z;
					}

					for (my $i=0; $i <= $#{ $self->{FAM}{MAP}{$fam}{POS} };$i++) {
						next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
						push @ { $de->{MAP_POS_LEFT} }, [	
							$x, $y + ($cc*$td1),
							-anchor => 'e', -text => sprintf("%6.2f",$self->{FAM}{MAP}{$fam}{POS}[$i]) ,
							-font => $font_haplo, -fill => $fh->{COLOR}
						];
						$cc++
					}
				}
				
				### position right side
				if ($self->{FAM}{SHOW_LEGEND_RIGHT}{$fam}) {
					$cc = 0; 
					my $x;
					if ($self->{FAM}{ALIGN_LEGEND}{$fam}) {
						$x = ( ($X_GLOB[-1]*$self->{FAM}{GITTER_X}{$fam}) + $self->{FAM}{LEGEND_SHIFT_RIGHT}{$fam} + $self->{FAM}{MARKER_POS_SHIFT}{$fam} ) * $z;
					} else {
						$x = ( ($X[-1]*$self->{FAM}{GITTER_X}{$fam}) + $self->{FAM}{LEGEND_SHIFT_RIGHT}{$fam} + $self->{FAM}{MARKER_POS_SHIFT}{$fam} ) * $z;
					}

					for (my $i=0; $i <= $#{ $self->{FAM}{MAP}{$fam}{POS} };$i++) {
						next unless $self->{FAM}{HAPLO}{$fam}{DRAW}[$i];
						push @ { $de->{MAP_POS_RIGHT} }, [	
							$x, $y + ($cc*$td1),
							-anchor => 'e', -text => sprintf("%6.2f",$self->{FAM}{MAP}{$fam}{POS}[$i]) ,
							-font => $font_haplo, -fill => $fh->{COLOR}
						];
						$cc++
					}
				}
				
			}
		}
	}
}

# Aligning 
#================
sub AlignMatrix {
#================	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $s = $self->{FAM}{STRUK}{$fam};
	my $m = $self->{FAM}{MATRIX}{$fam};
	my @s;
	my $cc = 1;
	my $cd = 0;
	my $ok = 1;
	my $max_x =  $self->{FAM}{X_SPACE}{$fam} * scalar keys % { $self->{FAM}{PID}{$fam} };
	
	foreach my $Y ( sort { $b <=> $a } keys % { $m->{YX2P} } ) {
		my %Save;
		foreach my $X ( sort { $a <=> $b } keys % { $m->{YX2P}{$Y} } ) {
			my $P = $m->{YX2P}{$Y}{$X} or die "No Person in XY $X $Y\n", Dumper($m);
			if ($X>$max_x) { return 0 }
			my ($fa,$mo) = ($self->{FAM}{SID2FATHER}{$fam}{$P},$self->{FAM}{SID2MOTHER}{$fam}{$P});
			next if ! $fa && ! $mo;
			
			### Geschwister von $P einschliesslich $P
			@s = keys %{$self->{FAM}{CHILDREN_COUPLE}{$fam}{$fa}{$mo}};
			
			my $str; $str .= $_ for @s;
			next if $Save{$str}; $Save{$str} = 1;

			### alle X Koordinaten der Geschwister
			my %k; foreach (@s) { 
				if (! $_ || ! defined $m->{P2XY}{$_}) {
					die Dumper(\@s, $m);
				}
				$k{ $m->{P2XY}{$_}{X} } = $_
			}
			my @sk = sort { $a <=> $b } keys %k;
			
			### translate parents into drawing compatible order in case of multiple mates
			($fa, $mo) = TranslateCoupleGroup($fam, 'FROM_MATRIX', $fa, $mo);
			
			my $Y_f = $m->{P2XY}{$fa}{Y};
			my $kf = $m->{P2XY}{$fa}{X};
			my $km = $m->{P2XY}{$mo}{X};
			my %k2 = ( $kf => $fa, $km => $mo);
			my @ek =  sort { $a <=> $b } keys %k2;
			my $mitte_c = sprintf("%1.0f", ($sk[0]+$sk[-1])/2);
			my $mitte_e = sprintf("%1.0f", ($kf+$km)/2);
			my $diff = $mitte_c-$mitte_e;			

			my $ind = 0;
			my $newpos1 = $sk[0]-$diff;
			my $newpos2 = $ek[0]+$diff;

			if (scalar (keys %{ $self->{FAM}{COUPLE}{$fam}{$k2{$ek[0]}}}) != 1) {
				$ind = 1;
				$newpos2 = $ek[1]+$diff;
			}

			if ( $diff < 0 ) {
				### Shift Kinder nach rechts ->
				ShiftRow($fam,$Y, $k{$sk[0]}, $newpos1);
				$self->{FAM}{PID_SAVE}{$fam}{$k2{$ek[0]}} = 1;
				return 0
			}

			elsif ( $diff > 0 )  {
				### Shift Eltern nach rechts ->
				unless (ShiftRow($fam,$Y_f, $k2{$ek[$ind]}, $newpos2,1)) {next};
				return  0

			}
			$cc++;
		}
	}
	return $cc;
}

#=========================
sub TranslateCoupleGroup {
#=========================
	my ($fam, $modus, $p1, $p2) = @_;
	my (%P, $flag, %ch, @S, @D1, @D2, %SAVE);
	my $m = $self->{FAM}{MATRIX}{$fam};
	my $c = $self->{FAM}{COUPLE}{$fam};
	my $cg = {};
	my $couple_from = join '==', nsort ($p1, $p2);
	
	## find everybody joined in couple group  
	foreach ( keys % { $self->{FAM}{COUPLE}{$fam}{$p1} }) {		
		$P{$_} = 1  if ! $self->{FAM}{CHILDREN}{$fam}{$p1}{$_}
	}
	W:while (1) {
		undef $flag;
		foreach my $p ( keys %P ) {
			foreach my $c ( keys % { $self->{FAM}{COUPLE}{$fam}{$p} }) {
				if (! $P{$c} && ! $self->{FAM}{CHILDREN}{$fam}{$p}{$c}) {
					$P{$c} = 1; $flag = 1
				}
			}
		}
		last W unless $flag
	}
	
	### examine multiple mate situation
	if (scalar keys %P > 2) {
		
		### locate each individual in the actual drawing
		### and store it in a hash sortable by x coordinate
		foreach my $p (keys %P) {
			if ($modus eq 'FROM_CANVAS') {
				my @co = $canvas->coords("SYM-$p") or return ($p1, $p2);								
				my $xm = sprintf("%1.3f", ($co[0]+$co[2])/2); 
				$ch{$xm}{$p} = 1
			}
			elsif ($modus eq 'FROM_MATRIX') { 
				if (! defined $m->{P2XY}{$p} ) {
					die "FROM_MATRIX error at pid $p\n"
				}
				
				$ch{$m->{P2XY}{$p}{X}}{$p} = 1
			}
		}
		
		### X-order of all mates as seen on canvas/matrix
		foreach my $x (sort { $a <=> $b } keys %ch) { 
			foreach my $p (keys % { $ch{$x} }) {
				push @S, $p; 
			}
		}
		
		foreach my $i (0 .. $#S-1) {
			push @D2, [ $S[$i], $S[$i+1] ];
		}
		
		### from @S derived order of couples for example (  [ p1, p3 ], [ p2, p3 ], [ p3, p4 ] )
		### list @S is screened for most right hand free mate
		foreach my $p1 (@S) {
			foreach my $p2 (@S) {
				next if $p1 eq $p2;
				if ($self->{FAM}{CHILDREN_COUPLE}{$fam}{$p1}{$p2} && ! $SAVE{$p1}{$p2} && ! $SAVE{$p2}{$p1}) {				
					my $str = join "==", nsort ($p1,$p2);
					my $last_i = $#D1 + 1;
					if ($str eq $couple_from) {
						return @ { $D2[$last_i] }
					}				
					push @D1, [ $p1, $p2 ];
					$SAVE{$p1}{$p2} = 1;
				}
			}
		}
	}
	return ($p1, $p2);
}



# Row Shift rechts: Shift erfolgt 'gleitend' d.h. Luecken werdend waehrend des
# shifts aufgefuellt
#=============
sub ShiftRow {
#=============	
	my ($fam, $Y, $pid, $NewPos, $flag) = @_;
	my $m = $self->{FAM}{MATRIX}{$fam};
	my $OldPos = $m->{P2XY}{$pid}{X};
	return if $NewPos == $OldPos;
	my (%SaveRow, %Freeze);

	### Wird benoetigt um sich kreuzende Zeichengruppen zu erkennen (shift wird unterbunden)
	foreach my $P (keys % { $self->{FAM}{PID_SAVE}{$fam} }) {
		next if $pid eq $P;
		next if $m->{P2XY}{$P}{Y} != $Y;
		my $X = $m->{P2XY}{$P}{X};
		$Freeze{$X} = $P if $X >= $OldPos;
	}
	(my $XL) = sort { $a <=> $b } keys %Freeze;

	if ($flag && $XL && ( $NewPos >= $XL) ) { return undef }

	foreach my $X (sort { $a <=> $b } keys % { 	$m->{YX2P}{$Y} } ) {
		$SaveRow{$m->{YX2P}{$Y}{$X}} =  $X ;
	}

	foreach my $st ( $OldPos .. $NewPos-1 ) {
		my (@right, @pid);
		foreach my $X (sort { $a <=> $b } keys % { 	$m->{YX2P}{$Y} } ) {
			if ($X >= $OldPos) {
				push @right, $X;
				push @pid, $m->{YX2P}{$Y}{$X}
			}
		}
		for (my $i = 0; $i <= $#right; $i++) {
			my $X = $right[$i];
			my $P = $pid[$i];
			delete $m->{YX2P}{$Y}{$X};
			$X++;
			$m->{YX2P}{$Y}{$X} = $P;
			$m->{P2XY}{$P}{X}  = $X;
			if ($right[$i+1]) {
				last if $right[$i+1]-$X-1 >= $self->{FAM}{X_SPACE}{$fam}
			}
		}
	}
	return 1;
}


# calculate all line coordinates
#=============
sub SetLines {
#=============	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $c = $canvas;	
	my $z = $self->{FAM}{ZOOM}{$fam};	
	my $d = $self->{FAM}{LINES}{$fam} = {};
	my $s = $self->{FAM}{STRUK}{$fam};
	my $gy = $self->{FAM}{GITTER_Y}{$fam};
	my $cf1 = $self->{FAM}{CROSS_FAKTOR1}{$fam};
	my $cd  = $self->{FAM}{CONSANG_DIST}{$fam};
	my $lsy = $self->{FAM}{LINE_SIBS_Y}{$fam};
	my $sz = $self->{FAM}{SYMBOL_SIZE}{$fam};
	my $lty = $self->{FAM}{LINE_TWINS_Y}{$fam};
	my $lcy = $self->{FAM}{LINE_CROSS_Y}{$fam};
	
	### calculate lines between parents			
	foreach my $parent_node (keys % { $self->{FAM}{PARENT_NODE}{$fam} }) {
		my ($par1, $par2) = @ { $self->{FAM}{PARENT_NODE}{$fam}{$parent_node} };
		
		### translate parents into "drawing compatible" order in case of multiple mates
		my ($par_t_1, $par_t_2) = TranslateCoupleGroup($fam, 'FROM_MATRIX', $par1, $par2);
		
		my @c1 = GetCanvasCoor($par_t_1,$fam);
		my @c2 = GetCanvasCoor($par_t_2,$fam);
								
		if ($c1[4]) { @c1[2,3] = @c1[4,5] }
		if ($c2[4]) { @c2[2,3] = @c2[4,5] }

		my (@X1, @X2);
		my ($x1, $x2);

		@X1 = @c1[0,2];
		@X2 = @c2[0,2];
								
		if ($X1[0] < $X2[0]) { ($x1, $x2) = ( $X1[1], $X2[0] ) }
		else { ($x1, $x2) = ( $X1[0], $X2[1] ) }

		my $xm1 = ($X1[0]+$X1[1])/2;
		my $xm2 = ($X2[0]+$X2[1])/2;
		
		### do not draw lines between couples up to the symbol middle point
		### to make possible the detection of symbol/line intersections 
		my $rr = $self->{FAM}{SYMBOL_SIZE}{$fam}*$z/4;
		if ($xm1 < $xm2) { $xm1 += $rr; $xm2 -= $rr }
		else { $xm1 -= $rr; $xm2 += $rr }
		
		my $ym1 = ($c1[1]+$c1[3])/2;
		my $ym2 = ($c2[1]+$c2[3])/2;								
		
		my $rd = ($xm2-$xm1)*$self->{FAM}{COUPLE_REL_DIST}{$fam};
		my $f = 2*$cd*$z; 
		
		### lines are stored as paths (end point one line = start point next line) for later drawing 
		### and also as single lines to count crosses : $d->{LINE_CROSS}
		
		### double line in case of consanguinity
		if (  ($self->{FAM}{LOOP}{$fam}{CONSANGUINE}{$par1} && $self->{FAM}{LOOP}{$fam}{CONSANGUINE}{$par1}{$par2}) ||
		($self->{FAM}{CONSANGUINE_MAN}{$fam}{$par1} && $self->{FAM}{CONSANGUINE_MAN}{$fam}{$par1}{$par2}) ) {
			
			### parents are at same y coordinates -> draw simple double line
			if ($ym1==$ym2) {									
				my $r = 
				[
					[ $xm1, $ym1-$cd*$z, $xm2, $ym2-$cd*$z ],
					[ $xm1, $ym1+$cd*$z, $xm2, $ym2+$cd*$z ]			 			
				];
				
				$d->{COUPLE}{$parent_node} = $r;								
				push  @ { $d->{LINE_CROSS} }, @$r
			}	
			### otherwise draw three double lines dependend on Y-axis location in two ways
			elsif ($ym1<$ym2) {
				$f *= -1 if $x1>$x2;
				$d->{COUPLE}{$parent_node} =
					[ 										
						[ $x1,$ym1-$cd*$z, $x1+$rd+$f, $ym1-$cd*$z ,$x1+$rd+$f, $ym2-$cd*$z ,$x2,$ym2-$cd*$z ],
						[ $x1,$ym1+$cd*$z, $x1+$rd,    $ym1+$cd*$z, $x1+$rd,    $ym2+$cd*$z, $x2,$ym2+$cd*$z ]
					];
					
				push @ { $d->{LINE_CROSS} }, 
				(				
					[ $x1,        $ym1-$cd*$z, $x1+$rd+$f, $ym1-$cd*$z ],
					[ $x1+$rd+$f, $ym1-$cd*$z, $x1+$rd+$f, $ym2-$cd*$z ],
					[ $x1+$rd+$f, $ym2-$cd*$z, $x2,        $ym2-$cd*$z ],	
					[ $x1,     $ym1+$cd*$z, $x1+$rd, $ym1+$cd*$z ],
					[ $x1+$rd, $ym1+$cd*$z, $x1+$rd, $ym2+$cd*$z ],
					[ $x1+$rd, $ym2+$cd*$z, $x2,     $ym2+$cd*$z ]
				)
			}
			else {
				$f *= -1 if $x1<$x2;
				$d->{COUPLE}{$parent_node} = 
				[
					[ $x2,$ym2-$cd*$z, $x2-$rd+$f, $ym2-$cd*$z, $x2-$rd+$f, $ym1-$cd*$z, $x1,$ym1-$cd*$z ],				
					[ $x2,$ym2+$cd*$z, $x2-$rd,    $ym2+$cd*$z ,$x2-$rd,    $ym1+$cd*$z ,$x1,$ym1+$cd*$z ]						
				];				
				push @ { $d->{LINE_CROSS} }, 
				( 										
					[ $x2,        $ym2-$cd*$z, $x2-$rd+$f, $ym2-$cd*$z ],
					[ $x2-$rd+$f, $ym2-$cd*$z, $x2-$rd+$f, $ym1-$cd*$z ],
					[ $x2-$rd+$f, $ym1-$cd*$z, $x1,        $ym1-$cd*$z ],	
					[ $x2,     $ym2+$cd*$z, $x2-$rd, $ym2+$cd*$z ],
					[ $x2-$rd, $ym2+$cd*$z, $x2-$rd, $ym1+$cd*$z ],
					[ $x2-$rd, $ym1+$cd*$z, $x1,     $ym1+$cd*$z ]
				)
			}
		}
				
		### no consanguinity --> draw only one line between parents (same cases as in consanguinity mode)
		else {
			if ($ym1==$ym2) {
				$d->{COUPLE}{$parent_node} = [ [ $x1, $ym1, $x2, $ym2 ] ];
				push  @ { $d->{LINE_CROSS} }, @ { $d->{COUPLE}{$parent_node} }
			}
			elsif ($ym1<$ym2) {
				$d->{COUPLE}{$parent_node} = 
				[ [ $x1,$ym1, $x1+$rd, $ym1 ,$x1+$rd, $ym2, $x2, $ym2 ]];
				
				push  @ { $d->{LINE_CROSS} }, 
				(
					[ $x1,     $ym1, $x1+$rd, $ym1 ],
					[ $x1+$rd, $ym1, $x1+$rd, $ym2 ],
					[ $x1+$rd, $ym2, $x2,     $ym2 ]
				)
			}
			else {
				$d->{COUPLE}{$parent_node} = 
				[[ $x2, $ym2, $x2-$rd, $ym2,$x2-$rd, $ym1 ,$x1, $ym1 ]];
				
				push  @ { $d->{LINE_CROSS} }, 
				(
					[ $x2,     $ym2, $x2-$rd, $ym2 ],
					[ $x2-$rd, $ym2, $x2-$rd, $ym1 ],
					[ $x2-$rd, $ym1, $x1,     $ym1 ]
				)
			}
		}
	}

	### calculate lines between sib groups (if not a single child)
	foreach my $parent_node (keys %{$d->{COUPLE}}) {
		my ($c1, $c2) = split '==', $parent_node;
		$d->{TWIN_LINES}{$parent_node} = [];
		my @children_org = keys %{$self->{FAM}{CHILDREN_COUPLE}{$fam}{$c1}{$c2}};
		my (%prtg, @children);    
		foreach (@children_org) {					
			### check if children  belong to twin groups
			### the code is not very pretty but works
			if ($self->{FAM}{SID2TWIN_GROUP}{$fam}{$_}) {				
				my $tg = $self->{FAM}{SID2TWIN_GROUP}{$fam}{$_};				
				### counterpart twins
				if (! $prtg{$tg}) {					
					my (%ch_twin,@cy_twin); 
					my @twins = keys % { $self->{FAM}{TWIN_GROUP2SID}{$fam}{$tg} }; 										
					### coordinates for all twins
					foreach my $twin (@twins) {
						my @co = GetCanvasCoor($twin,$fam);						
						if ($co[4]) { @co[2,3] = @co[4,5] }
						my $xm = sprintf("%1.3f", ($co[0]+$co[2])/2); 
						if ($ch_twin{$xm}) { $xm+= 0.001 }				
						my $ym = sprintf("%1.3f", ($co[1]+$co[3])/2);
						push @cy_twin, $ym;				
						$ch_twin{$xm}{YUP} = $ym-($sz/2*$z);
						$ch_twin{$xm}{YM} = $ym;						
					}
					
					### most upper Y coordinate
					@cy_twin = sort { $a <=> $b } @cy_twin;
					
					### middle x coordinate
					my @twins_x = sort { $a <=> $b } keys %ch_twin;
					my $xm = sprintf("%1.3f", ($twins_x[0]+$twins_x[-1])/2);
					
					### create array as reference storing needed coordinate information
					### for this twin group
					my $r = [ $xm, $cy_twin[0], \@twins, \%ch_twin];
					push @children, $r;					
					
					### mark twin group to process it only once
					$prtg{$tg} = 1
				}				
			}
			else {
				push @children, $_;
			}
		}
		
		if (scalar @children > 1) {
			
			my (@x, $yc, $y1, @cy, %ch, %prtg);
			my $r = $d->{SIB}{$parent_node} = [];

			### sort Y-coordinates 
			foreach my $ref (@children) {			
				if (! ref $ref) { 				 				
					my @co = GetCanvasCoor($ref,$fam);								 				
					if ($co[4]) { @co[2,3] = @co[4,5] }
					my $xm = sprintf("%1.3f", ($co[0]+$co[2])/2); 
					### work around to prevent overwriting children with same x coordinate
					if ($ch{$xm}) { $xm+= 0.001 }				
					my $ym = sprintf("%1.3f", ($co[1]+$co[3])/2);
					push @cy, $ym;					
					$ch{$xm}{YUP} = $co[1];
				}
				else {
					my ($xm, $ym) = @$ref;
					if ($ch{$xm}) { $xm+= 0.001 }
					push @cy, $ym;					
					$ch{$xm}{YUP} = $ym;
					$ch{$xm}{IS_TWIN} = $ref;
				}				 				
			}
											
			### Y- coordinate of horizontal		
			@cy = sort { $a <=> $b } @cy;
			my $y_up = $cy[0] - $lsy*$z;
			
			### X-coordinates sorted list of a child group
			my @child_x = sort { $a <=> $b } keys %ch;
												
			### left and right child
			my $K_F = shift @child_x;
			my $K_L = pop @child_x;	 
			
			### shorten the line if this child represent a twin group
			if ($ch{$K_F}{IS_TWIN}) { $ch{$K_F}{YUP} -= ($lty*$z) }
			if ($ch{$K_L}{IS_TWIN}) { $ch{$K_L}{YUP} -= ($lty*$z) }			
			
			### counting line crosses Y linker
			push  @ { $d->{LINE_CROSS} }, [ $K_F, $y_up, $K_L, $y_up ];			
															
			### most left child line + horizontal line + most right child line --> as path
			push @$r, [ $K_F, $ch{$K_F}{YUP},$K_F, $y_up, $K_L, $y_up, $K_L, $ch{$K_L}{YUP} ];
			
			### remaining children
			foreach my $xm (@child_x) {
				if ($ch{$xm}{IS_TWIN}) { $ch{$xm}{YUP} -= ($lty*$z)		}
				push @$r, [ $xm, $ch{$xm}{YUP}, $xm, $y_up ]
			}				
			
			### special case twin group -> add lines
			foreach my $child_x ($K_F, @child_x, $K_L) {
				### vertikal lines for cross check
				push  @ { $d->{LINE_CROSS} }, [ $child_x, $ch{$child_x}{YUP}, $child_x, $y_up ];			
				if ($ch{$child_x}{IS_TWIN}) {
					my ($x3, $y2, $cref, $href) = @{ $ch{$child_x}{IS_TWIN} };	
					my $y3 = $y2-($lsy*$z);				
					my $y4 = $y2-($lty*$z);				
					for ($x3, $y2, $y3, $y4) { $_ = sprintf("%1.3f", $_) }					
					my $r2 = $d->{TWIN_LINES}{$parent_node};				
					
					### connector line for every twin
					foreach my $twin (@$cref) {
						my @co = GetCanvasCoor($twin,$fam);		
						my $xm = sprintf("%1.3f", ($co[0]+$co[2])/2); 
						my $ym = sprintf("%1.3f", ($co[1]+$co[3])/2); 											
						my $xd = sprintf("%0.2f", $x3-$xm)+0;
						my $yd = ($ym-$y4);
						my $s = $sz/2*$z;
						my ($xp, $yp) = (0,$s);
						### calculate new start point for the angular lines at circle border
						if ($xd) {
							my $c = sqrt (($xd*$xd)+($yd*$yd));												
							my $f = $c/$s; $xp = $xd/$f; $yp = $yd/$f;					
						}																		
						push @$r2, [$xm+$xp, $ym-$yp, $x3, $y4];
						push @ { $d->{LINE_CROSS} }, [$xm+$xp, $ym-$yp, $x3, $y4];								
					}
					
					### extra middle line for monozygotic twins
					if ($self->{FAM}{SID2TWIN_TYPE}{$fam}{$cref->[0]} eq 'm') {						
						my @xsort = sort { $a <=> $b } keys %$href;						
						my $xs1 = ($xsort[0]+$x3)/2;
						my $ys1 = ($href->{$xsort[0]}{YM}+$y4)/2;
						my $xs2 = ($xsort[-1]+$x3)/2;
						my $ys2 = ($href->{$xsort[-1]}{YM}+$y4)/2;														
						push @$r2, [$xs1, $ys1, $xs2, $ys2];					
					}
				}				
			}																											
		}
		
		### save single childs for later queries
		else {
			if (! ref $children[0]) {
				my @co = GetCanvasCoor($children[0],$fam);				
				if ($co[4]) { @co[2,3] = @co[4,5] }
				$d->{CHILD}{$parent_node} = [ ($co[0]+$co[2])/2, $co[1] ]
			}
			else {
				### code for twins here
				$d->{CHILD}{$parent_node} = [ [ $children[0] ] ]
			}
		}
	}

	#### 3. calculate lines between parents and sibs
	foreach my $parent_node (keys %{$d->{COUPLE}}) {
		my $r1 = $d->{COUPLE}{$parent_node}[-1] or next;
		
		### most lower line between couples
		my ($x1, $x2, $y1) = ( $r1->[-4], $r1->[-2], $r1->[-3]);		
		($x1, $x2) = ($x2,$x1) if $x2<$x1;
		
		my ($xm1, $xd1) = ( ($x1+$x2)/2, $x2-$x1 );		
		for ($xm1, $xd1, $y1) { $_ = sprintf("%1.3f", $_) }
								
		### there is a sib group
		if ($d->{SIB}{$parent_node}) {
			my $r2 = $d->{SIB}{$parent_node}[0];			
			my ($x3, $x4, $y2) = ( $r2->[2], $r2->[4], $r2->[3] );
			
			($x3, $x4) = ($x4,$x3) if $x4<$x3;
			
			my ($xm2,$xd2) = ( ($x3+$x4)/2, $x4-$x3 );
			for ($xm2, $xd2, $y2) { $_ = sprintf("%1.3f", $_) }
								
			### splitting the group connector
			if ( ($x4 <= $xm1) || ($x3 >= $xm1) ) {			
				$d->{COUPLE_SIB}{$parent_node} = 
				[ [$xm1, $y1, $xm1, $y2-($cf1*$gy*$z),$xm2, $y2-($cf1*$gy*$z),$xm2, $y2] ];
				
				push  @ { $d->{LINE_CROSS} },	
				(
					[$xm1, $y1, $xm1, $y2-($cf1*$gy*$z)],
					[$xm1, $y2-($cf1*$gy*$z), $xm2, $y2-($cf1*$gy*$z)],
					[$xm2, $y2-($cf1*$gy*$z), $xm2, $y2]						
				);
			}

			### direct conection depending on group width
			else {
				if ( $xd1 <= $xd2  ) {
					$d->{COUPLE_SIB}{$parent_node} = [ [ $xm1, $y1, $xm1, $y2 ] ]
				} else {
					$d->{COUPLE_SIB}{$parent_node} = [ [ $xm2, $y1, $xm2, $y2 ] ]
				}
				push  @ { $d->{LINE_CROSS} }, @ { $d->{COUPLE_SIB}{$parent_node} };
			}
		}
		### single children
		elsif ($d->{CHILD}{$parent_node}) {
			### no twin group, regular children
			if (! ref $d->{CHILD}{$parent_node}[0]) {
				my ($x3, $y2) = ($d->{CHILD}{$parent_node}[0],  $d->{CHILD}{$parent_node}[1]);				
				### direct connection parent -> single child
				if ( ($x1 < $x3) && ($x2 > $x3) ) {
					$d->{COUPLE_SIB}{$parent_node} = [ [$x3,$y1,$x3,$y2] ];
					push  @ { $d->{LINE_CROSS} }, ([$x3,$y1,$x3,$y2]);
				}
				### split it
				else {
					my $y3 = $y2-($lsy*$z)+($sz/2*$z);
					$d->{COUPLE_SIB}{$parent_node} = [[ $xm1,$y1,$xm1,$y3,$x3,$y3,$x3,$y2 ]];					
					push  @{$d->{LINE_CROSS}},([$xm1,$y1,$xm1,$y3],[$xm1,$y3,$x3,$y3],[$x3,$y3,$x3,$y2])
				}												     	
      }
      else {
      	my $r = $d->{CHILD}{$parent_node}[0];
				my ($x3, $y2, $cref, $href) = @{$r->[0]};											
				my $y3 = $y2-($lsy*$z);				
				my $y4 = $y2-($lty*$z);				
				for ($x3, $y2, $y3, $y4) { $_ = sprintf("%1.3f", $_) }
			
				### direct connection parent -> single child
				if ( ($x1 < $x3) && ($x2 > $x3) ) {
					$d->{COUPLE_SIB}{$parent_node} = [ [ $x3, $y1, $x3, $y4 ] ];
					push  @ { $d->{LINE_CROSS} }, @ { $d->{COUPLE_SIB}{$parent_node} };
				}
				### split
				else {
					$d->{COUPLE_SIB}{$parent_node} = 
					[ [ $xm1, $y1, $xm1, $y3 ,$x3,  $y3 ,$x3,  $y4 ]	];
					
					push  @ { $d->{LINE_CROSS} },	
						(
							[ $xm1, $y1, $xm1, $y3 ],[$xm1, $y3, $x3,  $y3 ], [$x3,  $y3, $x3,  $y4 ]						
						)
				}
				
				my $r2 = $d->{TWIN_LINES}{$parent_node};				
				foreach my $twin (@$cref) {
					my @co = GetCanvasCoor($twin,$fam);		
					my $xm = sprintf("%1.3f", ($co[0]+$co[2])/2); 
					my $ym = sprintf("%1.3f", ($co[1]+$co[3])/2); 											
					my $xd = sprintf("%0.2f", $x3-$xm)+0;
					my $yd = ($ym-$y4);
					my $s = $sz/2*$z;
					my ($xp, $yp) = (0,$s);
					### calculate new start point for the angular lines at circle border
					if ($xd) {
						my $c = sqrt (($xd*$xd)+($yd*$yd));												
						my $f = $c/$s; $xp = $xd/$f;$yp = $yd/$f;									
					}																				
					push @$r2, [$xm+$xp, $ym-$yp, $x3, $y4];
					push @ { $d->{LINE_CROSS} }, [$xm+$xp, $ym-$yp, $x3, $y4];																	
				}	
				if ($self->{FAM}{SID2TWIN_TYPE}{$fam}{$cref->[0]} eq 'm') {						
					my @xsort = sort { $a <=> $b } keys %$href;						
					my $xs1 = ($xsort[0]+$x3)/2;
					my $ys1 = ($href->{$xsort[0]}{YM}+$y4)/2;
					my $xs2 = ($xsort[-1]+$x3)/2;
					my $ys2 = ($href->{$xsort[-1]}{YM}+$y4)/2;														
					push @$r2, [$xs1, $ys1, $xs2, $ys2];					
				}								  				   	
      }        			 
		}						
	}
	
	### special case -> parallel crossing line between two sib groups
	### upper one horizontal line to distinguish them
	foreach my $id1 (keys %{$d->{SIB}}) {
		my $A = $d->{SIB}{$id1}[0];
		my $C = $d->{COUPLE_SIB}{$id1}[0];
		foreach my $id2 (keys %{$d->{SIB}}) {
			my $B = $d->{SIB}{$id2}[0];
			next if $id1 eq $id2;
			next if ! ($A->[3] == $B->[3]);
			next if ! (($A->[2] < $B->[2]) && ($A->[4] > $B->[2])) ||
						(($B->[2] < $A->[2]) && ($B->[4] > $A->[2]));
						
			$A->[3] -= 6 * $z;
			$A->[5] -= 6 * $z;
			$C->[3] -= 6 * $z;
			$C->[5] -= 6 * $z if $C->[5];
			$C->[7] -= 6 * $z if $C->[7];
			@_ = @ {  $d->{SIB}{$id1} }; shift;
			$_->[3] -= 6 * $z foreach @_;		
		}
	}
		
}

#===================
sub CountLineCross {
#===================
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};		
	my $s = $self->{FAM}{LINES}{$fam}{LINE_CROSS};
	undef $self->{FAM}{CROSS_CHECK}{$fam};
	my $cr=0;
	my %DS;       
	     
	foreach my $r1 (@$s) {
		foreach my $r2 (@$s) {
			### do not compare same lines
			next if $r1 eq $r2;	
			### and do not count crosses of two lines that already have been counted
			$_ = join '_', sort ($r1,$r2);
			next if $DS{$_};
			$DS{$_}=1;						
			$cr += CrossCheck($fam,$r1,$r2);
		}
	}
	
	#### count symbols overlapping a line
	foreach my $r1 (@$s) {
		foreach my $pid (keys %{ $self->{FAM}{PID}{$fam}}) {
			my @co = GetCanvasCoor($pid,$fam);
			$cr += CrossCheck($fam,$r1, [@co]);
		}			
	}
	return $cr
}

#==================
sub GetCanvasCoor {
#==================
		my ($p,$fam) =  @_;
		
		my $z = $self->{FAM}{ZOOM}{$fam};	
		my $m = $self->{FAM}{MATRIX}{$fam};
		my $sz = $self->{FAM}{SYMBOL_SIZE}{$fam}/2;
		my $X = $m->{P2XY}{$p}{X};
		my $Y = $m->{P2XY}{$p}{Y};
		if (! defined $X || ! defined $Y) { die "GetCanvasCoor error at pid: $p", Dumper($self->{STRUK}) }
		my ($cx, $cy) = ($X*$self->{FAM}{GITTER_X}{$fam}, $Y*$self->{FAM}{GITTER_Y}{$fam});
		return (($cx-$sz)*$z, ($cy-$sz)*$z, ($cx+$sz)*$z, ($cy+$sz)*$z);
}

### new alghorithm for detecting parallele or crossed line intersection 07/2008
#===============
sub CrossCheck {
#===============
	my ($fam, $r1, $r2) = @_;
	
	my $z = $self->{FAM}{ZOOM}{$fam};
	my ($ax,$ay, $bx,$by) = @$r1;
	my ($cx,$cy, $dx,$dy) = @$r2;
	my $de = $self->{FAM}{CROSS_CHECK}{$fam};
	
	### round values
	foreach ($ax,$ay, $bx,$by, $cx,$cy, $dx,$dy) { $_ = sprintf("%0.0f", $_) }
	
	
	my $rn = ($ay-$cy)*($dx-$cx) - ($ax-$cx)*($dy-$cy);
	my $rd = ($bx-$ax)*($dy-$cy) - ($by-$ay)*($dx-$cx);
	
	### Lines are parallel and unable to cross
	return 0 if $rd ==0 && $rn !=0;
		
	## Lines are parallel and able to cross
	if ($rd==0 && $rn==0) {		
		if ($ax == $bx) {
			($ay, $by) = sort { $a <=> $b } ($ay, $by);
			($cy, $dy) = sort { $a <=> $b } ($cy, $dy);
			
			if ( (($cy>=$ay) && ($cy<$by)) || (($ay>=$cy) && ($ay<$dy))  ) { 			
				push @ { $self->{FAM}{CROSS_CHECK}{$fam} }, [ $ax-(5*$z),$ay-(5*$z),$ax+(5*$z),$ay+(5*$z), -width => 1, -outline => '#c0c0c0', -fill => '#000000'  ];	
				return 1 
			}			
		}
		
		else {
			($ax, $bx) = sort { $a <=> $b } ($ax, $bx);
			($cx, $dx) = sort { $a <=> $b } ($cx, $dx);
			if ( (($cx>=$ax) && ($cx<$bx)) || (($ax>=$cx) && ($ax<$dx))  ) {				
				push @ {$self->{FAM}{CROSS_CHECK}{$fam} }, [ $ax-5*$z,$ay-5*$z,$ax+5*$z,$ay+5*$z, -width => 1, -outline => '#c0c0c0', -fill => '#000000' ];		
				return 1 
			}
		}
		return 0		
	}
	
	my $intersection_ab = $rn / $rd;
	return 0 if ($intersection_ab<=0) or ($intersection_ab>=1);
				
	my $sn = ($ay-$cy)*($bx-$ax) - ($ax-$cx)*($by-$ay);                   
	my $intersection_cd = $sn / $rd;                   
	
	return 0 if ($intersection_cd<=0) or ($intersection_cd>=1);	
	
	my $intersection_x = $ax + $intersection_ab*($bx-$ax);
	my $intersection_y = $ay + $intersection_ab*($by-$ay);
	push @ { $self->{FAM}{CROSS_CHECK}{$fam} }, [ $intersection_x-(5*$z),$intersection_y-(5*$z),$intersection_x+(5*$z),$intersection_y+(5*$z), -width => 1, -outline => '#000000', -fill => '#c0c0c0'  ];	
	return 1;	
}


# examination of all mates and recursive mates of mates of child $child
# the list of mates is represented as simple drawing order @S
#===============
sub SetCouples {
#===============	
	my ($fam,$child) = @_;
	my (@S, @D ,@D2, %P, $flag, %SAVE);
	
	## find everybody joined in couple group  
	foreach ( keys % { $self->{FAM}{COUPLE}{$fam}{$child} }) {		
		$P{$_} = 1  if ! $self->{FAM}{CHILDREN}{$fam}{$child}{$_}
	}
	W:while (1) {
		undef $flag;
		foreach my $p ( keys %P ) {
			foreach my $c ( keys % { $self->{FAM}{COUPLE}{$fam}{$p} }) {
				if (! $P{$c} && ! $self->{FAM}{CHILDREN}{$fam}{$p}{$c}) {
					$P{$c} = 1; $flag = 1
				}
			}
		}
		last W unless $flag
	}
	
	### @S is drawing order of multiple mates in string form as ( p1, p2, p3, p4 )
	@S = keys %P;			
	return $child unless @S;
	ChangeOrder(\@S);
	if ($param->{SORT_COUPLE_BY_GENDER}) {
		@_ = (); 
		foreach (@S) { push @_, $_ if $self->{FAM}{SID2SEX}{$fam}{$_} == 1 }
		foreach (@S) { push @_, $_ if $self->{FAM}{SID2SEX}{$fam}{$_} != 1 }
		@_ = reverse(@_) if $param->{SORT_COUPLE_BY_GENDER} == 2;
		@S = @_
	}
	
	
	### from @S derived order of couples for example (  [ p1, p3 ], [ p2, p3 ], [ p3, p4 ] )
	### list @S is screened for most right hand free mate
	foreach my $p1 (@S) {
		foreach my $p2 (@S) {
			next if $p1 eq $p2;
			if ($self->{FAM}{CHILDREN_COUPLE}{$fam}{$p1}{$p2} && ! $SAVE{$p1}{$p2} && ! $SAVE{$p2}{$p1}) {				
				push @D, [ $p1, $p2 ];
				$SAVE{$p1}{$p2} = 1;
			}
		}
	}
	
	### additionaly store mate order in respect of centering children corect
	if ($#S > 1) {
		foreach my $i (0 .. $#S-1) {
			push @D2, [ $S[$i], $S[$i+1] ];
		}
	}
	else { push @D2, [ $S[0], $S[1] ] }	
	return [ [ @S ] , [ @D ], [ @D2] ];
}


# recalculate Y_SPACE
#===================
sub CanvasTrimYdim {
#===================
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $lw =  $self->{FAM}{HAPLO_TEXT_LW}{$fam};
	my $fs =  $self->{FAM}{FONT_HAPLO}{$fam}{SIZE};
	my $gy =  $self->{FAM}{GITTER_Y}{$fam};
	my $sy =  $self->{FAM}{Y_SPACE}{$fam};
	my $ysd = $self->{FAM}{Y_SPACE_DEFAULT}{$fam};
	my $lsy = $self->{FAM}{LINE_SIBS_Y}{$fam};
	my $sz =  $self->{FAM}{SYMBOL_SIZE}{$fam};
	
	### recalculate the Y space between the generations dependent to 
	### haplotype length and other space demanding drawing elements
	if ( BarTextOk($fam) ) {
		my $cc=1; for (5,4,3,2,1) { if ($self->{FAM}{CASE_INFO_SHOW}{$fam}{$_}) { $cc=$_;last  } }
		my $text = $self->{FAM}{FONT1}{$fam}{SIZE}*$cc;		
		my $c = 0; foreach ( @{ $self->{FAM}{HAPLO}{$fam}{DRAW} } ) { $c++ if $_ }				
		my $free_space = ($gy*$sy)-(2*$sz)-$text-$lsy;
		my $haplo_need_space = $c*($fs+($fs*$lw));
		my $add_space = sprintf ("%1.0f",(($haplo_need_space-$free_space)/$gy)+0.5);
		
		if ($add_space) {
			AddYspace($fam, $add_space);
			$self->{FAM}{Y_SPACE}{$fam} += $add_space; 
		}
	}
	### set distance between two generations to Y_SPACE_DEFAULT
	### this is the case if no haplotypes are there or map, alleles and 
	### marker information are not shown for haplotypes
	else {
		my $add_space = $ysd-$sy;
		if ( $add_space ) {		
			AddYspace($fam, $add_space);
			$self->{FAM}{Y_SPACE}{$fam} += $add_space;
		}		
	}
}

### adding $diff numbers of Y_SPACE space between two generations
#==============
sub AddYspace {
#==============
	my ($fam,$diff) = @_;
	my $m = $self->{FAM}{MATRIX}{$fam};
	my %t;
	### build translating hash
	my $c = 0; foreach my $Y (sort { $a <=> $b } keys %{ $m->{YX2P} }) {
		$t{$Y} = $Y + $c*$diff; $c++
	}

	### set Y
	$m->{YX2P} = {};
	foreach my $p (keys % { $m->{P2XY} } ) {
		my ($x,$y) = ($m->{P2XY}{$p}{X} , $t{$m->{P2XY}{$p}{Y}});
		$m->{P2XY}{$p}{Y} = $y;
		$m->{YX2P}{$y}{$x} = $p;
	}
}

# have bars marker, alleles or map positions?
#==============
sub BarTextOk {
#==============
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	my $h = $self->{FAM}{HAPLO}{$fam};
	if ( (keys %{$h->{PID}} && $self->{FAM}{SHOW_HAPLO_TEXT}{$fam})  ||
		($self->{FAM}{MAP}{$fam}{MARKER} && @{$self->{FAM}{MAP}{$fam}{MARKER}} && $self->{FAM}{SHOW_MARKER}{$fam})  ||
		($self->{FAM}{MAP}{$fam}{POS} 	&& @{$self->{FAM}{MAP}{$fam}{POS}} 	&& $self->{FAM}{SHOW_POSITION}{$fam}) ) {
		return 1
	} else { return 0 }	
}


#=================
sub DuplicatePid {
#=================	
	my ($fam, $p, $mate) = @_;					

	my $ci = $self->{FAM}{CASE_INFO}{$fam}{PID};
	$self->{FAM}{LOOP}{$fam}{DUPLICATION_COUNTER}{$p}++;
	my $dupc = $self->{FAM}{LOOP}{$fam}{DUPLICATION_COUNTER}{$p} + 1;
	my $pn = "$p($dupc)";
	
	$self->{FAM}{DUPLICATED_PID}{$fam}{$p}{$pn} = 1;         
	$self->{FAM}{DUPLICATED_PID_ORIG}{$fam}{$pn} = $p;
		
	my $k1 = $p . '==' . $mate;
	my $k2 = $pn . '==' . $mate;
	
	my @children = keys % {$self->{FAM}{CHILDREN_COUPLE}{$fam}{$p}{$mate} };
	
	delete $self->{FAM}{COUPLE}{$fam}{$p}{$mate};
	delete $self->{FAM}{COUPLE}{$fam}{$p} unless keys % {$self->{FAM}{COUPLE}{$fam}{$p}} ;
	delete $self->{FAM}{COUPLE}{$fam}{$mate}{$p};
	delete $self->{FAM}{COUPLE}{$fam}{$mate} unless keys % {$self->{FAM}{COUPLE}{$fam}{$mate}} ;		
	delete $self->{FAM}{CHILDREN_COUPLE}{$fam}{$p}{$mate};
	delete $self->{FAM}{CHILDREN_COUPLE}{$fam}{$p} unless keys %{$self->{FAM}{CHILDREN_COUPLE}{$fam}{$p}};		
	delete $self->{FAM}{CHILDREN_COUPLE}{$fam}{$mate}{$p};
	delete $self->{FAM}{CHILDREN_COUPLE}{$fam}{$mate} unless keys %{$self->{FAM}{CHILDREN_COUPLE}{$fam}{$mate}};		
	delete $self->{FAM}{SIBS}{$fam}{$k1};
	
	foreach (@children) {			
		$self->{FAM}{SIBS}{$fam}{$k2}{$_} = 1;			
		$self->{FAM}{CHILDREN_COUPLE}{$fam}{$mate}{$pn}{$_} = 1;
		$self->{FAM}{CHILDREN_COUPLE}{$fam}{$pn}{$mate}{$_} = 1;
		
		if ($self->{FAM}{SID2SEX}{$fam}{$p} == 1) { $self->{FAM}{SID2FATHER}{$fam}{$_} = $pn }
		else { $self->{FAM}{SID2MOTHER}{$fam}{$_} = $pn }
				
		delete $self->{FAM}{CHILDREN}{$fam}{$p}{$_} if $self->{FAM}{CHILDREN}{$fam}{$p}{$_};
		$self->{FAM}{CHILDREN}{$fam}{$pn}{$_} = 1;
	}
		
	delete $self->{FAM}{CHILDREN}{$fam}{$p} unless keys % {$self->{FAM}{CHILDREN}{$fam}{$p}};
	
	$self->{FAM}{SID2SEX}{$fam}{$pn} = $self->{FAM}{SID2SEX}{$fam}{$p};
	$self->{FAM}{SID2AFF}{$fam}{$pn} = $self->{FAM}{SID2AFF}{$fam}{$p};
	$self->{FAM}{COUPLE}{$fam}{$mate}{$pn} = 1;
	$self->{FAM}{COUPLE}{$fam}{$pn}{$mate} = 1;
	$self->{FAM}{PID}{$fam}{$pn}=1;
	$self->{FAM}{IS_DECEASED}{$fam}{$pn} = $self->{FAM}{IS_DECEASED}{$fam}{$p} if $self->{FAM}{IS_DECEASED}{$fam}{$p};
	
	### the new person ist founder per se
	$self->{FAM}{FOUNDER}{$fam}{$pn} = 1;
		
	### add case info fields
	if (keys % { $ci->{$p} }) {
		foreach (keys % { $ci->{$p} }) { $ci->{$pn}{$_} = $ci->{$p}{$_} }		
	}
	
	my $pid_old_new = $ci->{$p}{'Case_Info_1'} . "($dupc)";
	$ci->{$pn}{Case_Info_1}	= $pid_old_new;
	$self->{FAM}{PID2PIDNEW}{$fam}{$pid_old_new} = $pn;
	
	if (keys % { $self->{FAM}{LOOP}{$fam}{CONSANGUINE}{$p} }) {
		@_ = keys % {$self->{FAM}{LOOP}{$fam}{CONSANGUINE}{$p} };
		foreach (@_) {
			$self->{FAM}{LOOP}{$fam}{CONSANGUINE}{$pn}{$_} = 1;
			$self->{FAM}{LOOP}{$fam}{CONSANGUINE}{$_}{$pn} = 1;
		}
	}
	
	$_ = join '==', nsort($p, $mate);
	delete $self->{FAM}{PARENT_NODE}{$fam}{$_};
	$_ = join '==', nsort($pn,$mate);
	$self->{FAM}{PARENT_NODE}{$fam}{$_} = [ $pn, $mate ];
	
}

#==============
sub LoopBreak {
#==============	
	my $fam = shift @_ || $self->{GLOB}{CURR_FAM};
	foreach (keys % { $self->{FAM}{BREAK_LOOP_OK}{$fam} }) {
		next unless $self->{FAM}{BREAK_LOOP_OK}{$fam}{$_};
		my @p = split '==', $_;
		foreach (@p) { delete $self->{FAM}{LOOP}{$fam}{DROP_CHILDREN_FROM}{$_} if $self->{FAM}{LOOP}{$fam}{DROP_CHILDREN_FROM}{$_} }
			
		ChangeOrder(\@p);
		if (scalar @p > 2) {				
			my $p = shift @p;
			L:foreach (@p) {
				if ($self->{FAM}{COUPLE}{$fam}{$p}{$_}) {
					@p = ($p, $_); 
					last L;
				}
			}				
		}
		$self->{FAM}{LOOP}{$fam}{BREAK}{$p[0]}{$p[1]} = 1		
	}
			
	foreach my $p (keys % { $self->{FAM}{LOOP}{$fam}{BREAK} }) {
		foreach my $mate (keys % { $self->{FAM}{LOOP}{$fam}{BREAK}{$p} }) {					
			DuplicatePid($fam, $p, $mate);
		}				
	}
	1;
}

# icons are attached to Tk as base64 encoded gifs
#================
sub GetIconData {
#================
<<EOD;
R0lGODdhIAAgACIAACwAAAAAIAAgAIK15fwvLy/9IyRGRv///wAAAAAAAAAAAAADkgi63P4wyvmE
tWxoTd3Fy8Z1zCdkIll+6KYuZju+cZi+QK2IAxX8wKBwKHQQj8ifMbC6MAhQKEPZoCp0gKh0YeUy
YayFljD9lpsgxfhcNefCai17/naK5d4l+nSP0hVdWGt5bXtPeIBuiYZ9W4ttSZFAS5KSFFg8OHVp
AJk4mDc0cJ2hKqAun6OeonY7pZqwsRQJADs=
EOD
} 

#=============
sub GetMinus {
#=============
'R0lGODlhFwAXAPcAAKLIqZVUEKV7SaPDpZRSC9K1OOHATKFyRJJSDM2sMfXmZ7qEJJ+TcJFRC8qp
LvXnbLiBJJ6UcpBPCsimLffoc7mDKIxLCcilLPfrfbqGL56UcZ6/p5Oqoo+ioYugn5i0paHGqJ+2
qlpco3xoWPTjdb2KNqDFqICOm2JgmXl8so2Rvo+Ou3p0qGRfkFhboJPA7I+czX5bWqCWcaLFqW1w
lXV+t7PR787o+eDz+u35+vP499HR3mhhn4KJuqChx5CcmIKKnXJ+trDU8Lzc9czi89vp8+jw8/P2
9P//+O7s7WZZmoOPnZu3pVZWmp7A36vM6rnY88rh89rp8+fv8/H08/b28/3/+sXG2XR5l36Clm5/
tqDE4afI5rbW8cbf89Xm8+Hs8+rx8+7z8+709Ofw9HVxpJ/AqGpskn+byZ2+3qLE4idKieLs8+X1
+ouNupavpH+dyZq73Jm73NTl89ju+4eNvZWto3V4k2qAt6bE4LrQ5qDA36jJ6LPT8bva88Hd88Te
9MTf9MHf93BzqZ69p5qvpFFYnbTN5P///9Th8Jy93aXH5a3O67HT77PT8Lfa9Jy33mxrlqLHqWpp
lXCFutHj8Nvm8p693KDB4KTE46jK56TG5WNmpZetpaLBqmBdk2l/tYmt0pS42pi725q93Zu/3o2t
0lxio4WRnp+9qGpsk1lcnmh6s3GIvG+EumJvrFtalIycoJ2zpnV2kWpqkG1tkIWNmZ/Apw' 
. 'A' x 287 . 'CH5BAEAAAAALAAAAAAXABcA
AAj7AAEIHEiwoMGDAGTNolXLFsKHqlaxauXqFaxYDwt+AhVK1ChSpUydQpVR4CRKlSxdUoQpk6ZN
nDplLGToEKJEihYxauToEaRIGe/gyaNnD58+fv4ACiRoUMYzcOLIWUO16hw6dew8PIMmjZqqVdm0
cfPmYRYtW7h08fIFTBgxY8iUKdnEyRMoUaRMoVLFyhUsJYEEETKESBEjR5AkUbKkJAAaNWzcwJFD
xw4ePXz8cHwCRQoVK1i0cPECRgwZjgFw6ODhA4AQIkaQKKEhtUELFzBkqG2boIQJFCpE6E2wgYMH
EIYTF4gggYIFDJYLJFDAwAHpAgMIwM79YUAAOw=='

} 

#============
sub GetPlus {
#============
'R0lGODlhFwAXAPcAAKLIqZVUEKV7SaPDpZRSC9K1OOHATKFyRJJSDM2sMfXmZ7qEJJ+TcJFRC8qp
LvXnbLiBJJ6UcpBPCsimLffoc7mDKIxLCcilLPfrfbqGL56UcZ6/p5Oqoo+ioYugn5i0paHGqJ+2
qlpco3xoWPTjdb2KNqDFqICOm2JgmXl8so2Rvo+Ou3p0qGRfkFhboJPA7I+czX5bWqCWcaLFqW1w
lXV+t7PR787o+eDz+u35+vP499HR3mhhn4KJuqChx5CcmIKKnXJ+trDU8Lzc9czi89vp8+jw8/P2
9P//+O7s7WZZmoOPnZu3pVZWmp7A36vM6rnY88rh8ydKifH08/b28/3/+sXG2XR5l36Clm5/tqDE
4afI5rbW8cbf8+rx8+7z8+709Ofw9HVxpJ/AqGpskn+byZ2+3qLE4uLs8+X1+ouNupavpH+dyZq7
3Jm73NTl89ju+4eNvZWto3V4k2qAt6bE4LrQ5qDA36jJ6MHd88Te9MTf9MHf93BzqZ69p5qvpFFY
nbTN5P///9Th8Jy93bHT77PT8Lfa9Jy33mxrlqLHqWpplXCFutHj8Nvm8p693KDB4KTE46jK56TG
5WNmpZetpaLBqmBdk2l/tYmt0pS42pi725q93Zu/3o2t0lxio4WRnp+9qGpsk1lcnmh6s3GIvG+E
umJvrFtalIycoJ2zpnV2kWpqkG1tkIWNmZ/Apw'.'A' x 319 . 'CH5BAEAAAAALAAAAAAXABcA
AAj+AAEIHEiwoMGDAFStYtXKFUKEoUSNIlXK1ClUqR4StHQJUyZNmzh18vQJlEaBixg1cvSIEKRI
kiZRqqTxD6BAggYRkiKlkKFDiBJpnEOnjp07eHjm0bOHTx8/D8mwaeOGp1Upb+DEkRO1jJkzV3mi
SaNmzUMsWbRs4dKFp5cvYMKIGfOQSRMnT6BE4TmFShUrV04CCSJkCJEiRo4gSaJkyUkANGrYuIEj
h44dPHr4+HHSxAkUKVSsYNHCxQsYMWQ83sChg4cPIEKIGEGihIbHBy1cwJDhNu6CEiZQqBDhd8EG
Dh5AKG58IIIEChYwaD6QQAEDB6gPDCBAu/eTAQEAOw=='
} 

#============
sub GetHand {
#============
<<EOD;
R0lGODlhFwAXAPcAANTQyJmZmq2xvsjM2cvP28nN2sfM2cXJ1rK1w4WJlb68t7i1sm1xfba7y8jO
3srP3sjM3cbL28PI2aarvHJ2h7azsJmYmnZ6h66zwsfM29DV5M/U483S4czR4MrQ36+0xYeNnHh6
gdLOx7Syr3R5h8zR3tXZ5tba6Nba59PZ5tLX5dHV48/V48jM3LG2xXd8jJ+entPPx3Z4gL7CzuDk
79/i7tzh69ve6tnd6dfb6NXa59PY5s7T4qCltXJ1faWko4uOm+Xo8Ofq8uTn8OLl7+Hk7t/i7d3h
7Njc6dfb6b7C0m9zgM3Kw8PAunF0f9jb4vX2/Pj5/ezu9Obp8ePl7+Dk7t3i7Nre687T4XuAj7m3
s8jFv3FzfMLDy/f5/OHj6MTGzfT1+u7w9u3v9ert9Onr8uPm797i7djd6YeMm6WkpIiIjbi6wvT1
+f///4SIk3l9ifz9//X3+vL0+PDy9+7w9evt9Obo8OPn8Ojr85icqHt9hv3+/7m8wlpdaJmdpfz9
/vr6/Pf4+vL0+fLz+O/w9fDy+KGlr5CQk46PkqKlrZKVnoyNkYuLj9jZ3fr6+v7+/v39/vb3+fz8
/tna4Kyvt7G0voGCh8/LxKinprWzsM7Kw3+Bi/r7+7e4v+Xm6MjKzqGjq9XW225yfuzt8snM03V3
f6+yuOPj5mFmcsPEyrK0umlted/g5GNndNTV3N7g5nR4gYGDifHx80xQXsDBxrKzumtve+bm6Vtf
bZ6iq3V5gr+9uIuOmPb294OGkIOEiMLDyP/+/+rq7XJ2f3FzfYaIjK2sqaOlrczN0Xp8gqGgoMnK
z7K0u2Zqd+/v8X6BisTBu9HNxcnFv3h6g62vtnR4gs3O0rS1vFpebPf3+Hd6hNHNxsXCvJycnJiY
mtfY27m7wVlcaJqdpKirsn+Bh6Cfn7S2vP39/Z6hqZuam6+uq6CgoM3JwszIwYiJjn2AiXt9gwAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAXABcA
AAj/AAEIHEiwoMGDBd/Bi4ewoUBz59ClU7eOncOB3gR+A+cmnLhx5MpdpFbN2oJl19xgy+ZG27aL
yNwkU7aMmZtmziA9gwZgRMNebnz9AhbMja1bwoYRK9bLGEJZs9ysolXL6C1IuHLparMLoZpTblCl
UiWVFZ9Wrl7BimUwk6ZNnNx08vTJDahQbkSNIlXKVMFEihYxauTIzSNIkSQJmkSpEh1Llwru4eOm
j58/bgAFEiRnEKFChgwdQlRwDZs2bt7AiSNnDp06dsrcwZNHT4CCW7h08fIFTBgxY8iUmWKmyhk0
adQYbOLkCZQoUoRMCUKlipUrV7Bk0XLwB5AgQoYQYSli5MgNJCiSKFnSUMYMGjVs3MCRQ8eOHTx6
+Gg4gkQJEyegkIIKK7DQggsvwOCQBRdgkIEGG3DQgQcfgBDCRQAswEADDjwAQQQSTEABhgIFIMAA
BBRgwAEIJEDiizA6FBAAOw==
EOD
} 

#================
sub GetNextLeft {
#================
<<EOD;
R0lGODlhFwAXAMQAAICAgP///9TQyAV5AwaDBAV9BAeMBSifGwiVBQeIBQRzAwqeBnnRYwumB6bt
i5fkfojacGnHVVe8RUSxNQmZBgiRBQqiBwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEA
AAIALAAAAAAXABcAAAVHoCCOZGmeaKqubOu+ZgOXjTWPjbPcQv5QiIoh4fJBGBHJhNAyIpWHgmtx
YByu18ELcU0QCgMFzHBg8gTfs0irbrvf8Lh8FAIAOw==
EOD
}

#=================
sub GetNextRight {
#=================
<<EOD;
R0lGODlhFwAXAMQAAICAgP///9TQyANrAgRyAwV5BCifGwmXBgiRBQiLBAeFBAaABAqeBpHgeDSn
JgukB6Lqh4HVaXDMW1y/SkizOAyqCLL1lgysCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEA
AAIALAAAAAAXABcAAAVHoCCOZGmeaKqubOu+ZQWbDzOTTIPAV1UfEYniVbFAGsEJpeB6HJMUh2HQ
yhmuBim1dUAkFIvrdlaY3kSE8U19brvf8Lj8FQIAOw==
EOD
}

#=============
sub GetArrow {
#=============
'R0lGODlhFwAXAOYAANTQyAAAANPPx9DMxMrGvsXCusbCu8zIwNLOxs3JwcXBusC9tcO/t8vHwNHN
xc/Lw83KwsjEvSoqKsO/uMjEvH99eAMDA8fDvNDMxcnFvsK+t7+7tL25siIhIHVzcM7Kwo+Ojq2q
o7i0rYOAfBQUE7OwqUlJSZ6alTEwLmJfXLi1rsC8tdfX1llZWQUFBaWhm7Gtp7KvqOXl5dHR0PLz
8t/f38nJyqKfn3d3d/z8/O3t7ba2trCtpv////n5+Tw8PLSxqrazr' . 'A' x 248 .
'CH5BAEAAAAALAAAAAAXABcAAAdngACCg4SFhoeIiYqLiiBBjIkgAUCQhyAsATyVhSA9Oz+am4KdPjiZ
ogAgOTo7pqGVIDQ1NjemMZsgMjMuAb0BuCwtAS4vqCAmJygBKaiDIwEkzYMdAR7SABUWEtcAAdvc
4OHi4+SFgQA7'
} 

############################################################################
#                                    E  N  D                               #
############################################################################
