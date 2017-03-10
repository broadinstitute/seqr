import React from 'react'
import TinyMCE from 'react-tinymce'

class RichTextEditor extends React.Component {
  static propTypes = {
    id: React.PropTypes.string.isRequired,
    initialText: React.PropTypes.string,
  }

  componentDidMount() {
    window.tinyMCE.get(this.props.id).setContent(this.props.initialText)

    this.textAreaElement = document.getElementById(this.props.id)
    this.textAreaElement.name = this.props.id
  }

  render() {
    return <TinyMCE
      id={this.props.id}
      config={{
        forced_root_block: 'div',
        height: '500px',
        skin: 'lightgray',
        plugins: 'advlist autolink lists link image wordcount save contextmenu directionality textcolor colorpicker',
        menu: {},
        toolbar: 'bold italic underline | forecolor | bullist numlist outdent indent | fontselect',
        statusbar: false,
      }}
    />
  }
}

export default RichTextEditor


//http://socialcompare.com/en/comparison/javascript-online-rich-text-editors
//https://github.com/iDoRecall/comparisons/blob/master/JavaScript-WYSIWYG-editors.md
//https://quilljs.com/guides/comparison-with-other-rich-text-editors/

//TinyMCE - 227k minified. Lots of bugs. Has react integration https://www.tinymce.com/docs/integrations/react/
//Trumbowyg - 20k - fewer bugs - https://github.com/Alex-D/Trumbowyg
//https://github.com/ckeditor/ckeditor-dev


//import 'react-trumbowyg/dist/trumbowyg.min.css'
//import Trumbowyg from 'react-trumbowyg'

/*
 <Trumbowyg
 buttons={[
 ['formatting'],
 'btnGrp-semantic',
 ['link'],
 ['insertImage'],
 'btnGrp-justify',
 'btnGrp-lists',
 ['fullscreen'],
 ]}
 data="Hello, World!"
 placeholder="Type your text!"
 onChange={() => console.log('Change event fired')}
 />
 */
