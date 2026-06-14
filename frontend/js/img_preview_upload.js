imgInp.onchange = evt => {
  const [file] = imgInp.files
  if (file) {
    blah.src = URL.createObjectURL(file)
  }
}
//https://stackoverflow.com/questions/4459379/preview-an-image-before-it-is-uploaded