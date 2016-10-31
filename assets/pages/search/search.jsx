import React from 'react';
import ReactDOM from 'react-dom';

import BaseLayout from '../../components/base-layout'
import BreadCrumbs from '../../components/bread-crumbs';

import { InheritanceModeSelector } from './components/inheritance-mode-selector'
import { rootReducer } from './reducers/root-reducer'
import { createStore } from 'redux'
import { Provider } from 'react-redux'



ReactDOM.render(
    <Provider store={createStore(rootReducer)}>
        <BaseLayout>
            <div className="ui grid">
                <div className="row" style={{padding:"0px"}}>
                    <div className="sixteen wide column">
                        <BreadCrumbs breadcrumbs={["Search"]} />
                    </div>
                </div>
                <div className="row">
                    <InheritanceModeSelector />
                    <SearchButton />
                </div>
            </div>
        </BaseLayout>
    </Provider>,
    document.getElementById('reactjs-root')
)


/*
 const static_state = {
    info: {
         user: [{ }]
         projects: {1: {slug: "1kg", name: "1kg", family_ids: []}, 2: {slug: 'MYOSEQ_v20}},
         project_groups: [{id: 1, name: "My group1", project_ids: [1, 3, 10]}],
         families: [{id: 1, individuals: [] }],
         gene_lists: [{}],
    }
 }
 */

/*
{
  info: {
     user: [{ }]
     projects: {1: {slug: "1kg", name: "1kg", family_ids: []}, 2: {slug: 'MYOSEQ_v20}},
     project_groups: [{id: 1, name: "My group1", project_ids: [1, 3, 10]}],
     families: [{id: 1, individuals: [] }],
     gene_lists: [{}],
  }
  searchParameters: {
    individuals: {
        allow_multiple_project_selection: false,
        allow_multiple_family_selection: false,
        selected_project_ids: [1,2,3,4,5],
        selected_project_group_ids: [1,2,3,4,5],
        selected_family_ids: [1, ]
    },

    inheritance_modes: {
        homozygous-recessive: true,
        compound-het-recessive: false,
        x-linked-recessive:  true ,
        dominant: false,
        de-novo: true,
    },

    loci: {
        selected_gene_list_ids: [1, 2, 3, 5],
        gene_ids: ['ENSG123456','ENSG12456', 'ENSG12512525', 'ESNT125126'],

        ranges: [{chrom: '1', start: 10000, end:235235}],
        ranges_permit_partial_overlap: true
    }

    consequences : {
        frameshift: true,
        start_gain: true,
        stop_gain: true,
    }

    alleleFrequencies: {
        callset-internal: 0.01,
        exac: 0.01,
        exac-nfe: 0.01,
        exac_popmax: 0.01,
        1kg_wgs_phase3: 0.01,
        1kg_wgs_phase3_popmax: 0.01,
    }
    variantQC: {
        pass_only: true,
    }

    genotypeQC: {
         gq: 20,
         dp: 10,
         ab: 0.5
    }
    clinical: {
        in_clinvar: true | false | null
        in_omim: true | false | null
    }

   resultsFormat: {
        group_results_by: variant | family
        sort_results_by: {
            position: true,
            allele_frequency: false,
        }

        page:
        num_variants_per_page:
    }
  }

  searchState: {
    search_in_progress: false,
    search_error: false,
    search_succeeded: false,
  }

  searchResults: {
    error: null,

  }
}

*/

