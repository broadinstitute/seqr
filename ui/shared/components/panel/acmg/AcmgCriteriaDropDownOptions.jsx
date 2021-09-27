const ACMG_DROP_DOWN_OPTIONS = [
  {
    optionRowSpan: 3,
    optionTitle: 'Population Data',
    options: [
      [ // 0
        {
          description: 'MAF too high (Stand Alone)',
          key: 'BA1_S',
          values: [
            {
              key: 'BA_BA1_S_Yes',
              text: 'Y',
              value: 'BA_BA1_S_Yes',
            },
            {
              key: 'BA_BA1_S_No',
              text: 'N',
              value: 'BA_BA1_S_No',
            },
          ],
        },
      ],
      [], // empty cell
      [ // 1
        {
          description: 'LOW AF in pop db',
          key: 'PM2_P',
          values: [
            {
              key: 'PP_PM2_P_Yes',
              text: 'Y',
              value: 'PP_PM2_P_Yes',
            },
            {
              key: 'PP_PM2_P_No',
              text: 'N',
              value: 'PP_PM2_P_No',
            },
          ],
        },
      ],
      [ // 2
        {
          description: 'Absent (or rare) in pop db with coverage 20x',
          key: 'PM2_M',
          values: [
            {
              key: 'PM_PM2_M_Yes',
              text: 'Y',
              value: 'PM_PM2_M_Yes',
            },
            {
              key: 'PM_PM2_M_No',
              text: 'N',
              value: 'PM_PM2_M_No',
            },
          ],
        },
      ],
      [],
      [],
      [ // 3
        {
          description: 'MAF too high (Strong)',
          key: 'BS1_S',
          values: [
            {
              key: 'BS_BS1_S_Yes',
              text: 'Y',
              value: 'BS_BS1_S_Yes',
            },
            {
              key: 'BS_BS1_S_No',
              text: 'N',
              value: 'BS_BS1_S_No',
            },
          ],
        },
      ],
      [ // 4
        {
          description: 'MAF too high (Supporting)',
          key: 'BS1_P',
          values: [
            {
              key: 'BP_BS1_P_Yes',
              text: 'Y',
              value: 'BP_BS1_P_Yes',
            },
            {
              key: 'BP_BS1_P_No',
              text: 'N',
              value: 'BP_BS1_P_No',
            },
          ],
        },
      ],
      [ // 5
        {
          description: 'Proband Count - Supporting',
          key: 'PS4_P',
          values: [
            {
              key: 'PP_PS4_P_Yes',
              text: 'Y',
              value: 'PP_PS4_P_Yes',
            },
            {
              key: 'PP_PS4_P_No',
              text: 'N',
              value: 'PP_PS4_P_No',
            },
          ],
        },
      ],
      [ // 6
        {
          description: 'Proband Count - Moderate',
          key: 'PS4_M',
          values: [
            {
              key: 'PM_PS4_M_Yes',
              text: 'Y',
              value: 'PM_PS4_M_Yes',
            },
            {
              key: 'PM_PS4_M_No',
              text: 'N',
              value: 'PM_PS4_M_No',
            },
          ],
        },
      ],
      [ // 7
        {
          description: 'Case-control OR Proband Count',
          key: 'PS4_S',
          values: [
            {
              key: 'PS_PS4_S_Yes',
              text: 'Y',
              value: 'PS_PS4_S_Yes',
            },
            {
              key: 'PS_PS4_S_No',
              text: 'N',
              value: 'PS_PS4_S_No',
            },
          ],
        },
      ],
      [],
      [ // 8
        {
          description: 'Observ in unaffected',
          key: 'BS2_S',
          values: [
            {
              key: 'BS_BS2_S_Yes',
              text: 'Y',
              value: 'BS_BS2_S_Yes',
            },
            {
              key: 'BS_BS2_S_No',
              text: 'N',
              value: 'BS_BS2_S_No',
            },
          ],
        },
      ],
      [ // 9
        {
          description: 'BS2_Supporting',
          key: 'BS2_P',
          values: [
            {
              key: 'BP_BS2_P_Yes',
              text: 'Y',
              value: 'BP_BS2_P_Yes',
            },
            {
              key: 'BP_BS2_P_No',
              text: 'N',
              value: 'BP_BS2_P_No',
            },
          ],
        },
      ],
      [],
      [],
      [],
      [],
    ],
  },
  {
    optionRowSpan: 5,
    optionTitle: 'Computational and Predictive Data',
    options: [
      [ // 10
        {
          description: 'BP1_Strong',
          key: 'BP1_S',
          values: [
            {
              key: 'BS_BP1_S_Yes',
              text: 'Y',
              value: 'BS_BP1_S_Yes',
            },
            {
              key: 'BS_BP1_S_No',
              text: 'N',
              value: 'BS_BP1_S_No',
            },
          ],
        },
      ],
      [ // 11
        {
          description: 'Truncating disease causing variant missense',
          key: 'BP1_P',
          values: [
            {
              key: 'BP_BP1_P_Yes',
              text: 'Y',
              value: 'BP_BP1_P_Yes',
            },
            {
              key: 'BP_BP1_P_No',
              text: 'N',
              value: 'BP_BP1_P_No',
            },
          ],
        },
      ],
      [ // 12
        {
          description: 'PS1_Supporting',
          key: 'PS1_P',
          values: [
            {
              key: 'PP_PS1_P_Yes',
              text: 'Y',
              value: 'PP_PS1_P_Yes',
            },
            {
              key: 'PP_PS1_P_No',
              text: 'N',
              value: 'PP_PS1_P_No',
            },
          ],
        },
      ],
      [ // 13
        {
          description: 'PS1_Moderate',
          key: 'PS1_M',
          values: [
            {
              key: 'PM_PS1_M_Yes',
              text: 'Y',
              value: 'PM_PS1_M_Yes',
            },
            {
              key: 'PM_PS1_M_No',
              text: 'N',
              value: 'PM_PS1_M_No',
            },
          ],
        },
      ],
      [ // 14
        {
          description: 'Same AA change as establish pathogenic variant',
          key: 'PS1_S',
          values: [
            {
              key: 'PS_PS1_S_Yes',
              text: 'Y',
              value: 'PS_PS1_S_Yes',
            },
            {
              key: 'PS_PS1_S_No',
              text: 'N',
              value: 'PS_PS1_S_No',
            },
          ],
        },
      ],
      [],
      [ // 15
        {
          description: 'BP3_Strong',
          key: 'BP3_S',
          values: [
            {
              key: 'BS_BP3_S_Yes',
              text: 'Y',
              value: 'BS_BP3_S_Yes',
            },
            {
              key: 'BS_BP3_S_No',
              text: 'N',
              value: 'BS_BP3_S_No',
            },
          ],
        },
      ],
      [ // 16
        {
          description: 'In-frame indel in repeat region w/out known function',
          key: 'BP3_P',
          values: [
            {
              key: 'BP_BP3_P_Yes',
              text: 'Y',
              value: 'BP_BP3_P_Yes',
            },
            {
              key: 'BP_BP3_P_No',
              text: 'N',
              value: 'BP_BP3_P_No',
            },
          ],
        },
      ],
      [ // 17
        {
          description: 'PM5_Supporting',
          key: 'PM5_P',
          values: [
            {
              key: 'PP_PM5_P_Yes',
              text: 'Y',
              value: 'PP_PM5_P_Yes',
            },
            {
              key: 'PP_PM5_P_No',
              text: 'N',
              value: 'PP_PM5_P_No',
            },
          ],
        },
      ],
      [ // 18
        {
          description: 'Diff pathogenic missense variant at codon',
          key: 'PM5_M',
          values: [
            {
              key: 'PM_PM5_M_Yes',
              text: 'Y',
              value: 'PM_PM5_M_Yes',
            },
            {
              key: 'PM_PM5_M_No',
              text: 'N',
              value: 'PM_PM5_M_No',
            },
          ],
        },
      ],
      [ // 19
        {
          description: '>=2 diff path missense variants at codon',
          key: 'PM5_S',
          values: [
            {
              key: 'PS_PM5_S_Yes',
              text: 'Y',
              value: 'PS_PM5_S_Yes',
            },
            {
              key: 'PS_PM5_S_No',
              text: 'N',
              value: 'PS_PM5_S_No',
            },
          ],
        },
      ],
      [],
      [ // 20
        {
          description: 'Variant AA found in >= 3 mamals',
          key: 'BP4_S',
          values: [
            {
              key: 'BS_BP4_S_Yes',
              text: 'Y',
              value: 'BS_BP4_S_Yes',
            },
            {
              key: 'BS_BP4_S_No',
              text: 'N',
              value: 'BS_BP4_S_No',
            },
          ],
        },
      ],
      [ // 21
        {
          description: 'Computational evidence suggests no impact',
          key: 'BP4_P',
          values: [
            {
              key: 'BP_BP4_P_Yes',
              text: 'Y',
              value: 'BP_BP4_P_Yes',
            },
            {
              key: 'BP_BP4_P_No',
              text: 'N',
              value: 'BP_BP4_P_No',
            },
          ],
        },
      ],
      [ // 22
        {
          description: 'PSV1_Supporting',
          key: 'PSV1_P',
          values: [
            {
              key: 'PP_PSV1_P_Yes',
              text: 'Y',
              value: 'PP_PSV1_P_Yes',
            },
            {
              key: 'PP_PSV1_P_No',
              text: 'N',
              value: 'PP_PSV1_P_No',
            },
          ],
        },
      ],
      [ // 23
        {
          description: 'Null variant - Moderate',
          key: 'PVS1_M',
          values: [
            {
              key: 'PM_PVS1_M_Yes',
              text: 'Y',
              value: 'PM_PVS1_M_Yes',
            },
            {
              key: 'PM_PVS1_M_No',
              text: 'N',
              value: 'PM_PVS1_M_No',
            },
          ],
        },
      ],
      [ // 24
        {
          description: 'Null variant - Strong',
          key: 'PVS1_S',
          values: [
            {
              key: 'PS_PVS1_S_Yes',
              text: 'Y',
              value: 'PS_PVS1_S_Yes',
            },
            {
              key: 'PS_PVS1_S_No',
              text: 'N',
              value: 'PS_PVS1_S_No',
            },
          ],
        },
      ],
      [ // 25
        {
          description: 'Null variant & LOF known mechanism',
          key: 'PVS1_VS',
          values: [
            {
              key: 'PVS_PVS1_VS_Yes',
              text: 'Y',
              value: 'PVS_PVS1_VS_Yes',
            },
            {
              key: 'PVS_PVS1_VS_No',
              text: 'N',
              value: 'PVS_PVS1_VS_No',
            },
          ],
        },
      ],
      [],
      [],
      [ // 26
        {
          description: 'Computation evidence suggests impact',
          key: 'PP3_P',
          values: [
            {
              key: 'PP_PP3_P_Yes',
              text: 'Y',
              value: 'PP_PP3_P_Yes',
            },
            {
              key: 'PP_PP3_P_No',
              text: 'N',
              value: 'PP_PP3_P_No',
            },
          ],
        },
      ],
      [ // 27
        {
          description: 'PP3_Moderate',
          key: 'PP3_M',
          values: [
            {
              key: 'PM_PP3_M_Yes',
              text: 'Y',
              value: 'PM_PP3_M_Yes',
            },
            {
              key: 'PM_PP3_M_No',
              text: 'N',
              value: 'PM_PP3_M_No',
            },
          ],
        },
      ],
      [],
      [],
      [ // 28
        {
          description: 'BP7_Strong',
          key: 'BP7_S',
          values: [
            {
              key: 'BS_BP7_S_Yes',
              text: 'Y',
              value: 'BS_BP7_S_Yes',
            },
            {
              key: 'BS_BP7_S_No',
              text: 'N',
              value: 'BS_BP7_S_No',
            },
          ],
        },
      ],
      [ // 29
        {
          description: 'Silent or noncons splice (see below) with no predicted splice impact',
          key: 'BP7_P',
          values: [
            {
              key: 'BP_BP7_P_Yes',
              text: 'Y',
              value: 'BP_BP7_P_Yes',
            },
            {
              key: 'BP_BP7_P_No',
              text: 'N',
              value: 'BP_BP7_P_No',
            },
          ],
        },
      ],
      [ // 30
        {
          description: 'In-frame indel of 1-2 AA',
          key: 'PM4_S',
          values: [
            {
              key: 'PP_PM4_S_Yes',
              text: 'Y',
              value: 'PP_PM4_S_Yes',
            },
            {
              key: 'PP_PM4_S_No',
              text: 'N',
              value: 'PP_PM4_S_No',
            },
          ],
        },
      ],
      [ // 31
        {
          description: 'Protein length changing >2 AA in non- repeat region',
          key: 'PM4_M',
          values: [
            {
              key: 'PM_PM4_M_Yes',
              text: 'Y',
              value: 'PM_PM4_M_Yes',
            },
            {
              key: 'PM_PM4_M_No',
              text: 'N',
              value: 'PM_PM4_M_No',
            },
          ],
        },
      ],
      [ // 32
        {
          description: 'PM4_Strong',
          key: 'PM4S_S',
          values: [
            {
              key: 'PS_PM4S_S_Yes',
              text: 'Y',
              value: 'PS_PM4S_S_Yes',
            },
            {
              key: 'PS_PM4S_S_No',
              text: 'N',
              value: 'PS_PM4S_S_No',
            },
          ],
        },
      ],
      [],
    ],
  },
  {
    optionRowSpan: 3,
    optionTitle: 'Functional Data',
    options: [
      [],
      [],
      [ // 33
        {
          description: 'PM1_Supporting',
          key: 'PM1_P',
          values: [
            {
              key: 'PP_PM1_P_Yes',
              text: 'Y',
              value: 'PP_PM1_P_Yes',
            },
            {
              key: 'PP_PM1_P_No',
              text: 'N',
              value: 'PP_PM1_P_No',
            },
          ],
        },
      ],
      [ // 34
        {
          description: 'Mutation hotspot or fxnl domain',
          key: 'PM1_M',
          values: [
            {
              key: 'PM_PM1_M_Yes',
              text: 'Y',
              value: 'PM_PM1_M_Yes',
            },
            {
              key: 'PM_PM1_M_No',
              text: 'N',
              value: 'PM_PM1_M_No',
            },
          ],
        },
      ],
      [ // 35
        {
          description: 'PM1_Strong',
          key: 'PM1_S',
          values: [
            {
              key: 'PS_PM1_S_Yes',
              text: 'Y',
              value: 'PS_PM1_S_Yes',
            },
            {
              key: 'PS_PM1_S_No',
              text: 'N',
              value: 'PS_PM1_S_No',
            },
          ],
        },
      ],
      [],
      [],
      [],
      [ // 36
        {
          description: 'Missense in a gene with low rate of benign missense & path missense common',
          key: 'PP2_P',
          values: [
            {
              key: 'PP_PP2_P_Yes',
              text: 'Y',
              value: 'PP_PP2_P_Yes',
            },
            {
              key: 'PP_PP2_P_No',
              text: 'N',
              value: 'PP_PP2_P_No',
            },
          ],
        },
      ],
      [],
      [],
      [],
      [ // 37
        {
          description: 'Established fxnl study shows no deleterious effect',
          key: 'BS3_S',
          values: [
            {
              key: 'BS_BS3_S_Yes',
              text: 'Y',
              value: 'BS_BS3_S_Yes',
            },
            {
              key: 'BS_BS3_S_No',
              text: 'N',
              value: 'BS_BS3_S_No',
            },
          ],
        },
      ],
      [ // 38
        {
          description: 'BS3_Supporting',
          key: 'BS3_P',
          values: [
            {
              key: 'BP_BS3_P_Yes',
              text: 'Y',
              value: 'BP_BS3_P_Yes',
            },
            {
              key: 'BP_BS3_P_No',
              text: 'N',
              value: 'BP_BS3_P_No',
            },
          ],
        },
      ],
      [ // 39
        {
          description: 'Functional assay - Supporting',
          key: 'PS3_P',
          values: [
            {
              key: 'PP_PS3_P_Yes',
              text: 'Y',
              value: 'PP_PS3_P_Yes',
            },
            {
              key: 'PP_PS3_P_No',
              text: 'N',
              value: 'PP_PS3_P_No',
            },
          ],
        },
      ],
      [ // 40
        {
          description: 'Functional assay - Moderate',
          key: 'PS3_M',
          values: [
            {
              key: 'PM_PS3_M_Yes',
              text: 'Y',
              value: 'PM_PS3_M_Yes',
            },
            {
              key: 'PM_PS3_M_No',
              text: 'N',
              value: 'PM_PS3_M_No',
            },
          ],
        },
      ],
      [ // 41
        {
          description: 'Established fxnl study shows deleterious effect',
          key: 'PS3_S',
          values: [
            {
              key: 'PS_PS3_S_Yes',
              text: 'Y',
              value: 'PS_PS3_S_Yes',
            },
            {
              key: 'PS_PS3_S_No',
              text: 'N',
              value: 'PS_PS3_S_No',
            },
          ],
        },
      ],
      [],
    ],
  },
  {
    optionRowSpan: null,
    optionTitle: 'Segregation Data',
    options: [
      [ // 42
        {
          description: 'Lack of segregation in affected',
          key: 'BS4_S',
          values: [
            {
              key: 'BS_BS4_S_Yes',
              text: 'Y',
              value: 'BS_BS4_S_Yes',
            },
            {
              key: 'BS_BS4_S_No',
              text: 'N',
              value: 'BS_BS4_S_No',
            },
          ],
        },
      ],
      [ // 43
        {
          description: 'BS4_Supporting',
          key: 'BS4_P',
          values: [
            {
              key: 'BP_BS4_P_Yes',
              text: 'Y',
              value: 'BP_BS4_P_Yes',
            },
            {
              key: 'BP_BS4_P_No',
              text: 'N',
              value: 'BP_BS4_P_No',
            },
          ],
        },
      ],
      [ // 44
        {
          description: 'Coseg with disease Dominant: 3 segs Recessive',
          key: 'PP1_P',
          values: [
            {
              key: 'PP_PP1_P_Yes',
              text: 'Y',
              value: 'PP_PP1_P_Yes',
            },
            {
              key: 'PP_PP1_P_No',
              text: 'N',
              value: 'PP_PP1_P_No',
            },
          ],
        },
      ],
      [ // 45
        {
          description: 'Coseg with disease Dominant: 5 segs Recessive',
          key: 'PP1_M',
          values: [
            {
              key: 'PM_PP1_M_Yes',
              text: 'Y',
              value: 'PM_PP1_M_Yes',
            },
            {
              key: 'PM_PP1_M_No',
              text: 'N',
              value: 'PM_PP1_M_No',
            },
          ],
        },
      ],
      [ // 46
        {
          description: 'Coseg with disease Dominant: 7 segs Recessive',
          key: 'PP1_S',
          values: [
            {
              key: 'PS_PP1_S_Yes',
              text: 'Y',
              value: 'PS_PP1_S_Yes',
            },
            {
              key: 'PS_PP1_S_No',
              text: 'N',
              value: 'PS_PP1_S_No',
            },
          ],
        },
      ],
      [],
    ],
  },
  {
    optionRowSpan: 2,
    optionTitle: 'De Novo Data',
    options: [
      [],
      [],
      [ // 47
        {
          description: 'PM6_Supporting',
          key: 'PM6_P',
          values: [
            {
              key: 'PP_PM6_P_Yes',
              text: 'Y',
              value: 'PP_PM6_P_Yes',
            },
            {
              key: 'PP_PM6_P_No',
              text: 'N',
              value: 'PP_PM6_P_No',
            },
          ],
        },
      ],
      [ // 48
        {
          description: 'De novo (neither paternity or maternity confirmed)',
          key: 'PM6_M',
          values: [
            {
              key: 'PM_PM6_M_Yes',
              text: 'Y',
              value: 'PM_PM6_M_Yes',
            },
            {
              key: 'PM_PM6_M_No',
              text: 'N',
              value: 'PM_PM6_M_No',
            },
          ],
        },
      ],
      [ // 49
        {
          description: '>=2 independent occurences of PM6',
          key: 'PM6_S',
          values: [
            {
              key: 'PS_PM6_S_Yes',
              text: 'Y',
              value: 'PS_PM6_S_Yes',
            },
            {
              key: 'PS_PM6_S_No',
              text: 'N',
              value: 'PS_PM6_S_No',
            },
          ],
        },
      ],
      [],
      [],
      [],
      [ // 50
        {
          description: 'PS2_Supporting',
          key: 'PS2_P',
          values: [
            {
              key: 'PP_PS2_P_Yes',
              text: 'Y',
              value: 'PP_PS2_P_Yes',
            },
            {
              key: 'PP_PS2_P_No',
              text: 'N',
              value: 'PP_PS2_P_No',
            },
          ],
        },
      ],
      [ // 51
        {
          description: 'PS2_Moderate',
          key: 'PS2_M',
          values: [
            {
              key: 'PM_PS2_M_Yes',
              text: 'Y',
              value: 'PM_PS2_M_Yes',
            },
            {
              key: 'PM_PS2_M_No',
              text: 'N',
              value: 'PM_PS2_M_No',
            },
          ],
        },
      ],
      [ // 52
        {
          description: 'De novo (paternity and maternity confirmed)',
          key: 'PS2_S',
          values: [
            {
              key: 'PS_PS2_S_Yes',
              text: 'Y',
              value: 'PS_PS2_S_Yes',
            },
            {
              key: 'PS_PS2_S_No',
              text: 'N',
              value: 'PS_PS2_S_No',
            },
          ],
        },
      ],
      [ // 53
        {
          description: '>=2 independent occurences of PS2',
          key: 'PS2_VS',
          values: [
            {
              key: 'PVS_PS2_VS_Yes',
              text: 'Y',
              value: 'PVS_PS2_VS_Yes',
            },
            {
              key: 'PVS_PS2_VS_No',
              text: 'N',
              value: 'PVS_PS2_VS_No',
            },
          ],
        },
      ],
    ],
  },
  {
    optionRowSpan: null,
    optionTitle: 'Alleleic Data',
    options: [
      [ // 54
        {
          description: 'Met, BP2_Strong',
          key: 'BP2_S',
          values: [
            {
              key: 'BS_BP2_S_Yes',
              text: 'Y',
              value: 'BS_BP2_S_Yes',
            },
            {
              key: 'BS_BP2_S_No',
              text: 'N',
              value: 'BS_BP2_S_No',
            },
          ],
        },
      ],
      [ // 55
        {
          description: 'Observed in trans with dominant variant OR observed in cis with path variant',
          key: 'BP2_P',
          values: [
            {
              key: 'BP_BP2_P_Yes',
              text: 'Y',
              value: 'BP_BP2_P_Yes',
            },
            {
              key: 'BP_BP2_P_No',
              text: 'N',
              value: 'BP_BP2_P_No',
            },
          ],
        },
      ],
      [ // 56
        {
          description: 'Variant in trans does not meet LP/P criteria',
          key: 'PM3_P',
          values: [
            {
              key: 'PP_PM3_P_Yes',
              text: 'Y',
              value: 'PP_PM3_P_Yes',
            },
            {
              key: 'PP_PM3_P_No',
              text: 'N',
              value: 'PP_PM3_P_No',
            },
          ],
        },
      ],
      [ // 57
        {
          description: 'Detected in trans with P/LP variant (recessive disorders)',
          key: 'PM3_M',
          values: [
            {
              key: 'PM_PM3_M_Yes',
              text: 'Y',
              value: 'PM_PM3_M_Yes',
            },
            {
              key: 'PM_PM3_M_No',
              text: 'N',
              value: 'PM_PM3_M_No',
            },
          ],
        },
      ],
      [ // 58
        {
          description: '2-3 occurences of PM3 (see below)',
          key: 'PM3_S',
          values: [
            {
              key: 'PS_PM3_S_Yes',
              text: 'Y',
              value: 'PS_PM3_S_Yes',
            },
            {
              key: 'PS_PM3_S_No',
              text: 'N',
              value: 'PS_PM3_S_No',
            },
          ],
        },
      ],
      [ // 59
        {
          description: '>=4 occurences of PM3 (see below)',
          key: 'PM3_VS',
          values: [
            {
              key: 'PVS_PM3_VS_Yes',
              text: 'Y',
              value: 'PVS_PM3_VS_Yes',
            },
            {
              key: 'PVS_PM3_VS_No',
              text: 'N',
              value: 'PVS_PM3_VS_No',
            },
          ],
        },
      ],
    ],
  },
  {
    optionRowSpan: null,
    optionTitle: 'Other data',
    options: [
      [ // 60
        {
          description: 'Met, PB5_Strong',
          key: 'PB5_S',
          values: [
            {
              key: 'BS_PB5_S_Yes',
              text: 'Y',
              value: 'BS_PB5_S_Yes',
            },
            {
              key: 'BS_PB5_S_No',
              text: 'N',
              value: 'BS_PB5_S_No',
            },
          ],
        },
      ],
      [ // 61
        {
          description: 'Found in case with an alternative cause',
          key: 'BP5_P',
          values: [
            {
              key: 'BP_BP5_P_Yes',
              text: 'Y',
              value: 'BP_BP5_P_Yes',
            },
            {
              key: 'BP_BP5_P_No',
              text: 'N',
              value: 'BP_BP5_P_No',
            },
          ],
        },
      ],
      [ // 62
        {
          description: 'Patient phenotype or FH high specific for gene',
          key: 'PP4_P',
          values: [
            {
              key: 'PP_PP4_P_Yes',
              text: 'Y',
              value: 'PP_PP4_P_Yes',
            },
            {
              key: 'PP_PP4_P_No',
              text: 'N',
              value: 'PP_PP4_P_No',
            },
          ],
        },
      ],
      [ // 63
        {
          description: 'PP4_Moderate',
          key: 'PP4_M',
          values: [
            {
              key: 'PM_PP4_M_Yes',
              text: 'Y',
              value: 'PM_PP4_M_Yes',
            },
            {
              key: 'PM_PP4_M_No',
              text: 'N',
              value: 'PM_PP4_M_No',
            },
          ],
        },
      ],
      [ // 64
        {
          description: 'PP4_Strong',
          key: 'PP4_S',
          values: [
            {
              key: 'PS_PP4_S_Yes',
              text: 'Y',
              value: 'PS_PP4_S_Yes',
            },
            {
              key: 'PS_PP4_S_No',
              text: 'N',
              value: 'PS_PP4_S_No',
            },
          ],
        },
      ],
      [],
    ],
  },
]

export default ACMG_DROP_DOWN_OPTIONS
